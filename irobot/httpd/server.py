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

import asyncio
import logging
from threading import Lock, Thread
from typing import Optional

from aiohttp import web

import irobot.httpd._middleware as middleware
from irobot.authentication import BaseAuthHandler
from irobot.config.httpd import HTTPdConfig
from irobot.logging import LogWriter


class APIServer(LogWriter):
    """ HTTP API server interface """
    _loop:asyncio.AbstractEventLoop

    def __init__(self, httpd_config:HTTPdConfig, auth_handlers:List[BaseAuthHandler], logger:Optional[logging.Logger] = None) -> None:
        """
        Constructor: Start the event loop in a separate thread, which
        listens for and serves API requests

        @param   httpd_config   HTTPd configuration (HTTPdConfig)
        @param   auth_handlers  Authentication handlers (list of BaseAuthHandler)
        @param   logger         Logger
        @param   TODO...
        """
        super().__init__(logger=logger)
        self.log(logging.DEBUG, "Starting API server")

        self._loop_lock = Lock()
        self._loop_lock.acquire()

        # Start the event loop thread
        self._thread = Thread(target=self._init_loop, daemon=True)
        self._thread.start()

        with self._loop_lock:
            # Set up the web application and start listening on the
            # event loop once everything's ready
            app = web.Application(logger=logger,
                                  middlewares=[middleware.timeout,
                                               middleware.authentication])

            # Thread through application variables
            app["irobot_timeout"] = httpd_config.timeout
            app["irobot_auth_handlers"] = auth_handlers

            # TODO etc., etc....
            web.run_app(app, host=httpd_config.bind_address,
                             port=httpd_config.listen,
                             print=lambda *_: None,  # i.e. noop
                             loop=self._loop)

        # We don't need the loop lock any more
        del self._loop_lock

    def __del__(self) -> None:
        """ Tidy up after ourselves on Python GC """
        self.close()

    def _init_loop(self) -> None:
        """
        Initialise and start the event loop within the policy context
        (i.e., "thread", under the default policy)

        @note    Blocking
        """
        self._loop = asyncio.new_event_loop()
        self._loop_lock.release()

        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def close(self) -> None:
        """
        Graceful shutdown:
        * Close HTTPd listener
        * Stop the event loop and block until the thread terminates

        @note    Blocking
        """
        self.log(logging.DEBUG, "Shutting down API server")

        # TODO Close HTTPd listener
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join()