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

from collections import deque
from datetime import datetime
from inspect import getargspec, ismethod
from subprocess import CalledProcessError
from threading import BoundedSemaphore, Thread
from types import FunctionType, MethodType, StringType

from irobot.common import type_check
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


class iRODS(object):
    """ High level iRODS interface with iget pool management """
    def __init__(self, irods_config):
        """
        Constructor

        @param   irods_config  iRODS configuration
        """
        type_check(irods_config, iRODSConfig)
        self._config = irods_config

        self._iget_queue = deque()  # n.b., collections.deque is thread-safe
        self._iget_pool = BoundedSemaphore(self._config.max_connections())

        self._listeners = []

        self._running = True
        self._runner = Thread(target=self._thread_runner)
        self._runner.daemon = True
        self._runner.start()

    def _thread_runner(self):
        """ Thread runner to invoke igets """
        while self._running:
            if self._iget_queue:
                iget_args = self._iget_queue.popleft()
                with self._iget_pool:
                    Thread(target=self._iget, args=iget_args).start()

    def __del__(self):
        """ Stop thread runner on GC """
        self._running = False

    def add_listener(self, listener):
        """
        Add a listener for broadcast messages

        @param   listener  Listener (function of three arguments)
        """
        type_check(listener, FunctionType, MethodType)

        # Methods include the "self" argument
        arg_len = 4 if ismethod(listener) else 3
        if __debug__ and len(getargspec(listener).args) != arg_len:
            raise TypeError("Listener doesn't take 3 arguments")

        self._listeners.append(listener)

    def _broadcast(self, status, irods_path):
        """
        Broadcast a message to all the listeners

        @param   status      Message status (string)
        @param   irods_path  Path to data object on iRODS (string)
        """
        type_check(status, StringType)
        type_check(irods_path, StringType)

        broadcast_time = datetime.utcnow()
        for listener in self._listeners:
            listener(broadcast_time, status, irods_path)

    def get_dataobject(self, irods_path, local_path):
        """
        Enqueue retrieval of data object from iRODS and store it in the
        local filesystem, broadcasting retrieval status to listeners

        @param   irods_path  Path to data object on iRODS (string)
        @param   local_path  Local filesystem target file (string)
        """
        type_check(irods_path, StringType)
        type_check(local_path, StringType)

        _exists(irods_path)
        self._iget_queue.append((irods_path, local_path))
        self._broadcast(IGET_QUEUED, irods_path)

    def _iget(self, irods_path, local_path):
        """
        Perform the iget and broadcast status

        @note    Blocking

        @param   irods_path  Path to data object on iRODS (string)
        @param   local_path  Local filesystem target file (string)
        """
        try:
            self._broadcast(IGET_STARTED, irods_path)
            iget(irods_path, local_path)
            self._broadcast(IGET_FINISHED, irods_path)

        except CalledProcessError:
            self._broadcast(IGET_FAILED, irods_path)

    @staticmethod
    def get_metadata(irods_path):
        """
        Retrieve AVU and filesystem metadata for data object from iRODS

        @param   irods_path  Path to data object on iRODS (string)
        @return  AVU and filesystem metadata (tuple of list and dictionary)
        """
        type_check(irods_path, StringType)

        _exists(irods_path)
        baton_output = baton(irods_path)

        fs_keys = ["checksum", "size", "access", "timestamps"]
        return baton_output["avus"], {k:v for k, v in baton_output.items() if k in fs_keys}
