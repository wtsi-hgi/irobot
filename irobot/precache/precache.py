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
import os
import shutil
from typing import Dict, List, Optional
from uuid import uuid4

from irobot.config.precache import PrecacheConfig
from irobot.irods import iRODS, iGetStatus
from irobot.logging import LogWriter
from irobot.precache._checksummer import Checksummer, ChecksumStatus
from irobot.precache._types import ByteRange, ByteRangeChecksum
from irobot.precache.db import TrackingDB


def _new_precache_dir(precache_path:str) -> str:
    """
    Create a new precache directory path (i.e., just the string), by
    appending the precache base directory to a UUID4 split into 2-byte
    segments (i.e., so each level contains a maximum of 256 directories)

    @param   precache_path  Precache base path (string)
    @return  Precache directory path (string)
    """
    segments = map(lambda x: "".join(x), zip(*[iter(uuid4().hex)] * 2))
    return os.path.join(precache_path, *segments)

def _create_precache_dir(precache_dir:str) -> None:
    """
    Create a given precache directory on the filesystem (mkdir -p)

    @param   precache_dir  Full precache directory
    @note    Use with _new_precache_dir separately so the tracking DB
             can check for collisions
    @note    The directory is fully accessible to the user and only
             readable by the group
    """
    os.makedirs(precache_dir, mode=0o750)

def _delete_precache_dir(precache_dir:str) -> None:
    """
    Delete the top-level precache directory and its contents from the
    filesystem

    @param   precache_dir  Full precache directory
    @note    e.g., if deleting /foo/bar/quux, only quux will be removed
    """
    shutil.rmtree(precache_dir)


class Precache(LogWriter):
    """ High level precache interface """
    def __init__(self, precache_config:PrecacheConfig, irods:iRODS, logger:Optional[logging.Logger] = None) -> None:
        """
        Constructor

        @param   precache_config  Precache configuration (PrecacheConfig)
        @param   irods            iRODS interface (iRODS)
        @param   logger           Logger
        """
        super().__init__(logger=logger)
        self.log(logging.DEBUG, "Starting precache")

        self.config = precache_config

        db_in_precache = os.path.commonpath([precache_config.location, precache_config.index]) == precache_config.location
        self.tracker = TrackingDB(precache_config.index, db_in_precache, logger)

        self.irods = irods
        # TODO self.irods.add_listener(self.SOMETHING)

        self.checksummer = Checksummer(precache_config, logger)
        # TODO self.checksummer.add_listener(self.SOMETHING)

    def fetch_data(self, irods_path:str, byte_range:ByteRange = None, force:bool = False) -> Optional[bytes]:
        pass

    def fetch_metadata(self, irods_path:str, force:bool = False) -> Optional[Dict]:
        pass

    def fetch_checksums(self, irods_path:str, byte_range:ByteRange = None) -> Optional[List[ByteRangeChecksum]]:
        pass

    # TODO Public ETA functions for data and checksums
