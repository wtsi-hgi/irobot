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
from abc import abstractmethod
from threading import Lock, Timer
from typing import Any, Dict, Optional, Tuple

from requests import Response, Request, Session

from irobot.authentication._base import AuthenticatedUser, BaseAuthHandler
from irobot.config._base import BaseConfig
from irobot.logging import LogWriter


class HTTPAuthHandler(LogWriter, BaseAuthHandler):
    """ HTTP-based authentication handler with logging and caching """

    ## Implement these #################################################

    @abstractmethod
    def parse_auth_header(self, auth_header:str) -> Tuple[str, ...]:
        """
        Parse the authentication header

        @param   auth_header  Contents of the "Authorization" header (string)
        @return  Parsed contents (tuple of strings)
        """

    @abstractmethod
    def auth_request(self, *args:Tuple[str]) -> Request:
        """
        Create an authentication request

        @params  *args  Request arguments (strings)
        @return  Authentication request (requests.Request)
        """

    @abstractmethod
    def get_user(self, req:Request, res:Response) -> str:
        """
        Get the user from the authentication request and response

        @param   req  Authentication request (requests.Request)
        @param   res  Response from authentication URL (requests.Response)
        @return  Username (string)
        """

    ####################################################################

    def __init__(self, config:BaseConfig, logger:Optional[logging.Logger] = None) -> None:
        """
        Constructor

        @param   config  Arvados authentication configuration
        @param   logger  Logger
        """
        super().__init__(logger=logger)
        self._config = config

        # Initialise the cache, if required
        if self._config.cache:
            self.log(logging.DEBUG, "Creating authentication cache")
            self._cache:Dict[str, AuthenticatedUser] = {}
            self._cache_lock = Lock()
            self._schedule_cleanup()

    def _schedule_cleanup(self) -> None:
        """ Initialise and start the clean up timer """
        self._cleanup_timer = Timer(self._config.cache.total_seconds(), self._cleanup)
        self._cleanup_timer.daemon = True
        self._cleanup_timer.start()

    def __del__(self) -> None:
        """ Cancel any running clean up timer on GC """
        if self._config.cache and self._cleanup_timer.is_alive():
            self._cleanup_timer.cancel()

    def _cleanup(self) -> None:
        """ Clean up expired entries from the cache """
        with self._cache_lock:
            self.log(logging.DEBUG, "Cleaning authentication cache")
            for key, user in list(self._cache.items()):
                if not user.valid(self._config.cache):
                    del self._cache[key]

        self._schedule_cleanup()

    def _validate_request(self, req:Request) -> Optional[Response]:
        """
        Make an authentication request to check for validity

        @param   req  Authentication request (requests.Request)
        @return  Authentication response (requests.Response; None on failure)
        """
        session = Session()
        res = session.send(req.prepare())

        if 200 <= res.status_code < 300:
            self.log(logging.DEBUG, "Authenticated")
            return res

        if res.status_code in [401, 403]:
            self.log(logging.WARNING, "Couldn't authenticate")
        else:
            res.raise_for_status()

        return None

    def authenticate(self, auth_header:str) -> Optional[AuthenticatedUser]:
        """
        Validate the authorisation header

        @param   auth_header  Contents of the "Authorization" header (string)
        @return  Authenticated user (AuthenticatedUser)
        """
        try:
            parsed = self.parse_auth_header(auth_header)

        except ValueError:
            self.log(logging.WARNING, "Couldn't parse authentication header")
            return None

        # Check the cache
        if self._config.cache:
            with self._cache_lock:
                if auth_header in self._cache:
                    user = self._cache[auth_header]
                    if user.valid(self._config.cache):
                        self.log(logging.DEBUG, f"Authenticated user \"{user.user}\" from cache")
                        return user

                    # Clean up expired users
                    del self._cache[auth_header]

        req = self.auth_request(*parsed)
        res = self._validate_request(req)
        if res:
            user = AuthenticatedUser(self.get_user(req, res))

            # Put validated user in the cache
            if self._config.cache:
                with self._cache_lock:
                    self._cache[auth_header] = user

            return user

        return None
