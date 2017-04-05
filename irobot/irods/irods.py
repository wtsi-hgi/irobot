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
from datetime import datetime
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
from subprocess import CalledProcessError
from typing import Optional

from irobot.common import Listenable
from irobot.config.irods import iRODSConfig
from irobot.irods._api import baton, iget, ils
from irobot.logging import LogWriter


def _exists(irods_path:str) -> None:
    """
    Check data object exists on iRODS

    @param   irods_path  Path to data object on iRODS (string)
    """
    try:
        ils(irods_path)

    except CalledProcessError:
        raise IOError(f"Data object \"{irods_path}\" inaccessible")


iGetStatus = Enum("iGetStatus", "queued started finished failed")


class iRODS(Listenable, LogWriter):
    """ High level iRODS interface with iget pool management """
    def __init__(self, irods_config:iRODSConfig, logger:Optional[logging.Logger] = None) -> None:
        """
        Constructor

        @param   irods_config  iRODS configuration
        @param   logger        Logger
        """
        self._config = irods_config

        # Initialise superclasses (multiple inheritance is a PITA)
        super().__init__(logger=logger)
        self.add_listener(self._broadcast_iget_to_log)

        self.log(logging.DEBUG, "Starting iget pool")
        self._iget_pool = ThreadPoolExecutor(max_workers=self._config.max_connections)
        atexit.register(self._iget_pool.shutdown)

    def __del__(self) -> None:
        """ Shutdown the thread pool on GC """
        self.log(logging.DEBUG, "Shutting down iget pool")
        self._iget_pool.shutdown()

    def _broadcast_iget_to_log(self, _timestamp:datetime, status:iGetStatus, irods_path:str) -> None:
        """
        Log all broadcast iget messages

        @param   status      iGet status (iGetStatus)
        @param   irods_path  Path to data object on iRODS (string)
        """
        level = logging.WARNING if status == iGetStatus.failed else logging.INFO
        self.log(level, f"iget {status.name} for {irods_path}")

    def get_dataobject(self, irods_path:str, local_path:str) -> None:
        """
        Enqueue retrieval of data object from iRODS and store it in the
        local filesystem, broadcasting retrieval status to listeners

        @param   irods_path  Path to data object on iRODS (string)
        @param   local_path  Local filesystem target file (string)
        """
        _exists(irods_path)
        self.broadcast(iGetStatus.queued, irods_path)
        self._iget_pool.submit(self._iget, irods_path, local_path)

    def _iget(self, irods_path:str, local_path:str) -> None:
        """
        Perform the iget and broadcast status

        @note    Blocking

        @param   irods_path  Path to data object on iRODS (string)
        @param   local_path  Local filesystem target file (string)
        """
        try:
            self.broadcast(iGetStatus.started, irods_path)
            iget(irods_path, local_path)
            self.broadcast(iGetStatus.finished, irods_path)

        except CalledProcessError:
            self.broadcast(iGetStatus.failed, irods_path)

    def get_metadata(self, irods_path:str) -> None:
        """
        Retrieve AVU and filesystem metadata for data object from iRODS

        @param   irods_path  Path to data object on iRODS (string)
        @return  AVU and filesystem metadata (tuple of list and dictionary)
        """
        _exists(irods_path)

        self.log(logging.INFO, f"Getting metadata for {irods_path}")
        baton_output = baton(irods_path)

        fs_keys = ["checksum", "size", "access", "timestamps"]
        return baton_output["avus"], {k:v for k, v in baton_output.items() if k in fs_keys}
