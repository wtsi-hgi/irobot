"""
Copyright (c) 2017 Genome Research Ltd.

Author: Christopher Harrison <ch12@sanger.ac.uk>

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your
option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
Public License for more details.

You should have received a copy of the GNU General Public License along
with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import logging
import math
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from hashlib import md5
from typing import List, Optional, Tuple

import irobot.common.canon as canon
from irobot.common import Listenable
from irobot.config.precache import PrecacheConfig
from irobot.logging import LogWriter


ByteRange = Optional[Tuple[int, int]]  # 0 <= from < to <= data size; None for everything
ByteRangeChecksum = Tuple[ByteRange, str]


_RE_CHECKSUM_RECORD = re.compile(r"""
    ^(?:                                # Anchor to start of string
        (?:
            (?P<whole> \* )             # Whole data
            |
            (?:
                (?P<from> \d+ )         # Range from
                -
                (?P<to> \d+ )           # Range to
            )
        )
        \t                              # Tab
        (?P<checksum> [a-z0-9]{32} )    # MD5 sum
    )$                                  # Anchor to end of string
""", re.VERBOSE | re.IGNORECASE)

def _parse_checksum_record(record:str) -> ByteRangeChecksum:
    """
    Parse (but don't validate) checksum record

    @param   record  Record (string)
    @return  Byte range size (ByteRangeSize)
    """
    match = _RE_CHECKSUM_RECORD.match(record)

    if not match:
        raise SyntaxError("Invalid checksum record")

    byte_range = None if match.group("whole") else (int(match.group("from")), int(match.group("to")))
    return (byte_range, match.group("checksum"))


def _checksum(filename:str, chunk_size:int, byte_range:ByteRange = None) -> Tuple[str, List[ByteRangeChecksum]]:
    """
    Calculate the file chunk checksums

    @param   filename    Full path of filename to checksum (string)
    @param   chunk_size  Chunk size in bytes (int)
    @param   byte_range  Byte range to checksum (ByteRange; None for all)
    @return  Tuple of the filename and list of checksums covering the
             specified range (Tuple of string and list of ByteRangeChecksum)
    """
    whole_file = (byte_range is None)
    file_size = os.stat(filename).st_size

    chunk_checksums:List[ByteRangeChecksum] = []
    if whole_file:
        whole_checksum = md5()
        byte_range = (0, file_size)

    # Calculate chunk boundaries
    chunks:List[ByteRange] = []
    range_from, range_to = byte_range
    range_to = min(range_to, file_size)
    for i in range(range_from // chunk_size, (range_to // chunk_size) + 1):
        chunk_from = max(i * chunk_size, range_from)
        chunk_to = min((i + 1) * chunk_size, range_to)

        if chunk_from < chunk_to:
            chunks.append((chunk_from, chunk_to))

    # Do the checksumming
    with open(filename, "rb") as fd:
        for chunk in chunks:
            chunk_from, chunk_to = chunk
            chunk_length = chunk_to - chunk_from

            fd.seek(chunk_from)
            chunk_data = fd.read(chunk_length)
            if len(chunk_data) == 0:
                break

            checksum = md5(chunk_data)
            chunk_checksums.append((chunk, checksum.hexdigest()))

            if whole_file:
                whole_checksum.update(chunk_data)

    if whole_file:
        # Prepend checksum for whole file
        chunk_checksums = [(None, whole_checksum.hexdigest())] + chunk_checksums

    return filename, chunk_checksums


class Checksummer(Listenable, LogWriter):
    """ Checksummer """
    def __init__(self, precache_config:PrecacheConfig, logger:Optional[logging.Logger] = None) -> None:
        """
        Constructor

        @param   precache_config  Precache configuration
        @param   logger           Logger
        """
        # Currently we are only interested in the chunk_size config,
        # but that may change in future so just bring in everything
        self._config = precache_config

        # Initialise logging superclass
        super().__init__(logger=logger)
        self.add_listener(self._broadcast_to_log)

        self.pool = ThreadPoolExecutor()

    def __del__(self) -> None:
        """ Shutdown the thread pool on GC """
        self.pool.shutdown()

    def _broadcast_to_log(self, timestamp:datetime, *args, **kwargs) -> None:
        """
        Log all checksummer broadcasts (i.e., upon completion)

        @note    *args will be the precache path
        """
        self.log(logging.INFO, f"Checksumming completed for {args[0]}")

    def generate_checksum_file(self, precache_path:str) -> None:
        """
        Start calculating the checksums (to file) for the precache data

        The calculated checksum file is of the form:

        *\t<checksum>
        0-<chunk_size>\t<checksum>
        <chunk_size>-<2*chunk_size>\t<checksum>
        ...

        Where the first line shows the checksum of the whole data, then
        the subsequent lines show the checksums for each chunk

        @param   precache_path  Path to the precache data
        """
        # TODO
        pass

    def get_checksummed_blocks(self, precache_path:str, byte_range:ByteRange = None) -> List[ByteRangeChecksum]:
        """
        Retrieve the checksum blocks of the precache data (from file;
        calculating overlaps/intersections when necessary), or the
        checksum of the entire data

        @param   precache_path  Path to the precache data (string)
        @param   byte_range     Byte range for which to get checksums (ByteRange)
        @return  List of checksums covering the specified range (list of ByteRangeChecksum)
        """
        checksum_file = os.path.join(precache_path, "checksums")

        if not os.path.exists(checksum_file):
            raise FileNotFoundError(f"Checksums not available for {precache_path}")

        if byte_range is None:
            # Return checksum for whole file (i.e., first record)
            with open(checksum_file, "rt") as fd:
                checksum_line = fd.readline()
            
            return [_parse_checksum_record(checksum_line)]

        data_size = os.stat(os.path.join(precache_path, "data")).st_size
        byte_from, byte_to = byte_range

        try:
            assert 0 <= byte_from < byte_to <= data_size
        
        except AssertionError:
            raise IndexError("Invalid data range")

        # TODO

    def calculate_checksum_filesize(self, data_size:int) -> int:
        """
        Calculate the size of the checksum file based on the size of the
        input data

        @param   data_size  Input data size in bytes (int)
        @return  Checksum file size in bytes (int)
        """
        chunk_size = self._config.chunk_size
        chunks = math.ceil(data_size / chunk_size)

        chunk_index_bytes = sum(map(lambda x: len(f"{x * chunk_size}-{min(data_size, (x + 1) * chunk_size)}"), range(chunks)))
        chunk_checksum_bytes = chunks * 32
        chunk_whitespace_bytes = chunks * 2  # \t and \n

        return ( 35 # = "*" + \t + <checksum> + \n
               + chunk_index_bytes
               + chunk_checksum_bytes
               + chunk_whitespace_bytes )
