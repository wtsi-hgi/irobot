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
from collections import deque
from subprocess import CalledProcessError
from threading import BoundedSemaphore, Thread
from types import NoneType, StringType

from irobot.common import Listener, LogWriter, type_check_arguments
from irobot.config.irods import iRODSConfig
from irobot.irods._api import baton, iget, ils


# Status constants
IGET_QUEUED = "queued"
IGET_STARTED = "started"
IGET_FINISHED = "finished"
IGET_FAILED = "failed"


def _exists(irods_path):
    """
    Check data object exists on iRODS

    @param   irods_path  Path to data object on iRODS (string)
    """
    try:
        ils(irods_path)

    except CalledProcessError:
        raise IOError("Data object \"%s\" inaccessible" % irods_path)


class iRODS(Listener, LogWriter):
    """ High level iRODS interface with iget pool management """
    @type_check_arguments(irods_config=iRODSConfig, logger=(logging.Logger, NoneType))
    def __init__(self, irods_config, logger=None):
        """
        Constructor

        @param   irods_config  iRODS configuration
        """
        self._config = irods_config

        # Initialise superclasses (multiple inheritance is a PITA)
        super(iRODS, self).__init__(logger=logger)
        self.add_listener(self._broadcast_iget_to_log)

        self._iget_queue = deque()  # n.b., collections.deque is thread-safe
        self._iget_pool = BoundedSemaphore(self._config.max_connections())

        self._running = True
        self._runner = Thread(target=self._thread_runner)
        self._runner.daemon = True
        self._runner.start()

    def _thread_runner(self):
        """ Thread runner to invoke igets """
        self.log(logging.DEBUG, "Starting iget pool")
        while self._running:
            if self._iget_queue:
                iget_args = self._iget_queue.popleft()
                with self._iget_pool:
                    Thread(target=self._iget, args=iget_args).start()

    def __del__(self):
        """ Stop thread runner on GC """
        self.log(logging.DEBUG, "Shutting down iget pool")
        self._running = False

    def _broadcast_iget_to_log(self, timestamp, *args, **kwargs):
        """
        Log all broadcast iget messages

        @note    *args will be a tuple of the status and iRODS path
        """
        level = logging.WARNING if args[0] == IGET_FAILED else logging.INFO
        self.log(level, "iget: %s %s" % args)

    @type_check_arguments(irods_path=StringType, local_path=StringType)
    def get_dataobject(self, irods_path, local_path):
        """
        Enqueue retrieval of data object from iRODS and store it in the
        local filesystem, broadcasting retrieval status to listeners

        @param   irods_path  Path to data object on iRODS (string)
        @param   local_path  Local filesystem target file (string)
        """
        _exists(irods_path)
        self._iget_queue.append((irods_path, local_path))
        self.broadcast(IGET_QUEUED, irods_path)

    def _iget(self, irods_path, local_path):
        """
        Perform the iget and broadcast status

        @note    Blocking

        @param   irods_path  Path to data object on iRODS (string)
        @param   local_path  Local filesystem target file (string)
        """
        try:
            self.broadcast(IGET_STARTED, irods_path)
            iget(irods_path, local_path)
            self.broadcast(IGET_FINISHED, irods_path)

        except CalledProcessError:
            self.broadcast(IGET_FAILED, irods_path)

    @type_check_arguments(irods_path=StringType)
    def get_metadata(self, irods_path):
        """
        Retrieve AVU and filesystem metadata for data object from iRODS

        @param   irods_path  Path to data object on iRODS (string)
        @return  AVU and filesystem metadata (tuple of list and dictionary)
        """
        _exists(irods_path)

        self.log(logging.INFO, "Getting metadata for %s" % irods_path)
        baton_output = baton(irods_path)

        fs_keys = ["checksum", "size", "access", "timestamps"]
        return baton_output["avus"], {k:v for k, v in baton_output.items() if k in fs_keys}
