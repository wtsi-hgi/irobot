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

from irobot.common import AsyncTaskStatus, Listenable, WorkerPool
from irobot.config.irods import iRODSConfig
from irobot.irods._api import iRODSError, baton, iget, ils
from irobot.irods._types import Metadata
from irobot.logging import LogWriter


def _exists(irods_path:str) -> None:
    """
    Check data object exists on iRODS

    @param   irods_path  Path to data object on iRODS (string)
    """
    try:
        ils(irods_path)

    except iRODSError as e:
        if e.error == (317000, "USER_INPUT_PATH_ERR"):
            raise FileNotFoundError(f"Data object \"{irods_path}\" not found")

        elif e.error == (818000, "CAT_NO_ACCESS_PERMISSION"):
            raise PermissionError(f"Not authorised to access data object \"{irods_path}\"")

        else:
            raise IOError(f"Data object \"{irods_path}\" inaccessible")


class iRODS(Listenable, LogWriter, WorkerPool):
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

        self.log(logging.INFO, "Starting iget pool")
        self._iget_pool = ThreadPoolExecutor(max_workers=self._config.max_connections)
        atexit.register(self._iget_pool.shutdown)

    def __del__(self) -> None:
        """ Shutdown the thread pool on GC """
        self.log(logging.DEBUG, "Shutting down iget pool")
        self._iget_pool.shutdown()

    def _broadcast_iget_to_log(self, _timestamp:datetime, status:AsyncTaskStatus, irods_path:str, local_path:str) -> None:
        """
        Log all broadcast iget messages

        @param   status      iGet status (AsyncTaskStatus)
        @param   irods_path  Path to data object on iRODS (string)
        @param   local_path  Local filesystem target file (string)
        """
        level = logging.WARNING if status == AsyncTaskStatus.failed else logging.INFO
        self.log(level, f"iget {status.name} for {irods_path} to {local_path}")

    @property
    def workers(self) -> int:
        """ The total/maximum number of workers """
        return self._config.max_connections

    def get_dataobject(self, irods_path:str, local_path:str) -> None:
        """
        Enqueue retrieval of data object from iRODS and store it in the
        local filesystem, broadcasting retrieval status to listeners

        @param   irods_path  Path to data object on iRODS (string)
        @param   local_path  Local filesystem target file (string)
        """
        _exists(irods_path)
        self.broadcast(AsyncTaskStatus.queued, irods_path, local_path)
        self._iget_pool.submit(self._iget, irods_path, local_path)

    def _iget(self, irods_path:str, local_path:str) -> None:
        """
        Perform the iget and broadcast status

        @note    Blocking

        @param   irods_path  Path to data object on iRODS (string)
        @param   local_path  Local filesystem target file (string)
        """
        try:
            self.broadcast(AsyncTaskStatus.started, irods_path, local_path)
            iget(irods_path, local_path)
            self.broadcast(AsyncTaskStatus.finished, irods_path, local_path)

        except CalledProcessError:
            self.broadcast(AsyncTaskStatus.failed, irods_path, local_path)

    def get_metadata(self, irods_path:str) -> Metadata:
        """
        Retrieve AVU and filesystem metadata for data object from iRODS

        @param   irods_path  Path to data object on iRODS (string)
        @return  AVU and filesystem metadata (tuple of list and dictionary)
        """
        _exists(irods_path)

        self.log(logging.INFO, f"Getting metadata for {irods_path}")
        return baton(irods_path)
