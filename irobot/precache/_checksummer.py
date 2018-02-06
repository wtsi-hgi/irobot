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

import atexit
import logging
import math
import os
import re
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from hashlib import md5
from typing import List, Optional, Tuple

from irobot.common import AsyncTaskStatus, ByteRange, Listenable, WorkerPool
from irobot.config import PrecacheConfig
from irobot.logs import LogWriter

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


def _parse_checksum_record(record: str) -> ByteRange:
    """
    Parse (but don't validate) checksum record

    @param   record  Record (string)
    @return  Byte range (ByteRange)
    """
    match = _RE_CHECKSUM_RECORD.match(record)

    if not match:
        raise SyntaxError("Invalid checksum record")

    range_from = 0 if match["whole"] else int(match["from"])
    range_to   = -1 if match["whole"] else int(match["to"])
    return ByteRange(range_from, range_to, match["checksum"])


def _checksum(filename: str, chunk_size: int, byte_range: Optional[ByteRange]=None) -> Tuple[str, List[ByteRange]]:
    """
    Calculate the file chunk checksums

    @param   filename    Full path of filename to checksum (string)
    @param   chunk_size  Chunk size in bytes (int)
    @param   byte_range  Byte range to checksum (ByteRange; None for all)
    @return  Tuple of the filename and list of checksums covering the
             specified range (Tuple of string and list of ByteRange)
    """
    assert chunk_size > 0

    whole_file = (byte_range is None)
    file_size = os.stat(filename).st_size

    chunk_checksums: List[ByteRange] = []
    if whole_file:
        whole_checksum = md5()
        byte_range = ByteRange(0, file_size)

    # Calculate chunk boundaries
    chunks: List[ByteRange] = []
    range_from, range_to, _ = byte_range
    range_to = min(range_to, file_size)
    for i in range(range_from // chunk_size, (range_to // chunk_size) + 1):
        chunk_from = max(i * chunk_size, range_from)
        chunk_to = min((i + 1) * chunk_size, range_to)

        if chunk_from < chunk_to:
            chunks.append(ByteRange(chunk_from, chunk_to))

    # Do the checksumming
    with open(filename, "rb") as fd:
        for chunk in chunks:
            chunk_length = chunk.finish - chunk.start

            fd.seek(chunk.start)
            chunk_data = fd.read(chunk_length)

            checksum = md5(chunk_data)
            chunk_checksums.append(ByteRange(chunk.start, chunk.finish, checksum.hexdigest()))

            if whole_file:
                whole_checksum.update(chunk_data)

    if whole_file:
        # Prepend checksum for whole file
        chunk_checksums = [ByteRange(0, -1, whole_checksum.hexdigest())] + chunk_checksums

    return filename, chunk_checksums


class Checksummer(Listenable, LogWriter, WorkerPool):
    """ Checksummer """
    def __init__(self, precache_config: PrecacheConfig, logger: Optional[logging.Logger]=None) -> None:
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

        self.log(logging.INFO, "Starting checksumming pool")
        self.pool = ThreadPoolExecutor()
        atexit.register(self.pool.shutdown)

    def __del__(self) -> None:
        """ Shutdown the thread pool on GC """
        self.log(logging.DEBUG, "Shutting down checksumming pool")
        self.pool.shutdown()

    def _broadcast_to_log(self, _timestamp: datetime, status: AsyncTaskStatus, precache_path: str) -> None:
        """
        Log all checksummer broadcasts (i.e., upon completion)

        @param   status         Checksumming status (AsyncTaskStatus)
        @param   precache_path  Precache path (string)
        """
        self.log(logging.INFO, f"Checksumming {status.name} for {precache_path}")

    def _start_checksumming(self, precache_path: str) -> Tuple[str, List[ByteRange]]:
        """
        Start calculating the checksums for the precache data and notify
        listeners that we've started

        @param   precache_path  Precache path (string)
        """
        self.broadcast(AsyncTaskStatus.started, precache_path)

        data_file = os.path.join(precache_path, "data")
        return _checksum(data_file, self._config.chunk_size)

    def _write_checksum_file(self, checksum_future: Future) -> None:
        """
        Write checksums to file and broadcast completion to listeners

        @param   checksum_future  Future passed from executor with
                                  result from _checksum function (Future)
        """
        if checksum_future.done():
            filename, chunk_checksums = checksum_future.result()

            precache_path = os.path.dirname(filename)
            checksum_file = os.path.join(precache_path, "checksums")

            with open(checksum_file, "wt") as fd:
                for index_from, index_to, checksum in chunk_checksums:
                    index = "*" if (index_from, index_to) == (0, -1) else f"{index_from}-{index_to}"
                    fd.write(f"{index}\t{checksum}\n")

            self.broadcast(AsyncTaskStatus.finished, precache_path)

    @property
    def workers(self) -> int:
        """ The total/maximum number of workers """
        # FIXME This relies on an undocumented API call
        return self.pool._max_workers

    def generate_checksum_file(self, precache_path: str) -> None:
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
        future = self.pool.submit(self._start_checksumming, precache_path)
        future.add_done_callback(self._write_checksum_file)

    def get_checksummed_blocks(self, precache_path: str, byte_range: Optional[ByteRange]=None) -> List[ByteRange]:
        """
        Retrieve the checksum blocks of the precache data (from file;
        calculating overlaps/intersections when necessary), or the
        checksum of the entire data

        @param   precache_path  Path to the precache data (string)
        @param   byte_range     Byte range for which to get checksums (ByteRange)
        @return  List of checksums covering the specified range (list of ByteRange)
        """
        checksum_file = os.path.join(precache_path, "checksums")

        if not os.path.exists(checksum_file):
            raise FileNotFoundError(f"Checksums not available for {precache_path}")

        with open(checksum_file, "rt") as fd:
            whole_record = fd.readline()

            if byte_range is None:
                # Return checksum for whole file (i.e., first record)
                return [_parse_checksum_record(whole_record)]

            data_file = os.path.join(precache_path, "data")
            data_size = os.stat(data_file).st_size
            byte_from, byte_to, _ = byte_range

            try:
                assert 0 <= byte_from < byte_to <= data_size
            except AssertionError:
                raise IndexError("Invalid data range")

            output: List[ByteRange] = []

            # Read through records to find intersection
            while True:
                # Read the next chunk record
                chunk_record = fd.readline()
                if not chunk_record:
                    break

                # Parse the chunk and break if we've got all we want
                chunk_from, chunk_to, _ = this_chunk = _parse_checksum_record(chunk_record)
                if byte_to < chunk_from:
                    break

                if byte_from <= chunk_from < chunk_to <= byte_to:
                    # Chunk is completely contained within range, so we
                    # can just read it from file
                    output.append(this_chunk)

                else:
                    # ...otherwise we need to calculate the checksums
                    # for the overlapping/contained sections
                    to_calculate = ByteRange(max(chunk_from, byte_from), min(chunk_to, byte_to))

                    # Submit calculation of partial chunk checksum to
                    # the pool and block on result for output
                    # FIXME? Is this the behaviour we want, or should we
                    # bypass the pool and calculate immediately?
                    future = self.pool.submit(_checksum, data_file, self._config.chunk_size, to_calculate)
                    _, checksums = future.result()

                    output += checksums

            return output

    def calculate_checksum_filesize(self, data_size: int) -> int:
        """
        Calculate the size of the checksum file based on the size of the
        input data

        @param   data_size  Input data size in bytes (int)
        @return  Checksum file size in bytes (int)
        """
        chunk_size = self._config.chunk_size
        chunks = math.ceil(data_size / chunk_size)

        chunk_index_bytes = sum(
            map(lambda x: len(f"{x * chunk_size}-{min(data_size, (x + 1) * chunk_size)}"), range(chunks)))
        chunk_checksum_bytes = chunks * 32
        chunk_whitespace_bytes = chunks * 2  # \t and \n

        return (35  # = "*" + \t + <checksum> + \n
                + chunk_index_bytes
                + chunk_checksum_bytes
                + chunk_whitespace_bytes)
