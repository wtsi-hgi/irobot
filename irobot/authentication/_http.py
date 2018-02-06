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
from abc import abstractmethod
from threading import Lock, Timer
from typing import Dict, NamedTuple, Optional

from aiohttp import ClientSession, ClientResponse

from irobot.authentication._base import AuthenticatedUser, BaseAuthHandler
from irobot.authentication.parser import HTTPAuthMethod, ParseError, auth_parser
from irobot.config import Configuration
from irobot.logging import LogWriter


class HTTPValidatorParameters(NamedTuple):
    """ Parameters for the HTTP validator """
    url: str                        # URL to make the authentication response to
    payload: str                    # Challenge response payload
    method: str = "GET"             # HTTP method
    headers: Dict[str, str] = {}    # Additional request headers


class BaseHTTPAuthHandler(LogWriter, BaseAuthHandler):
    """ Base HTTP-based authentication handler with logging and caching """

    ## Implement these #################################################

    @abstractmethod
    def match_auth_method(self, challenge_response: HTTPAuthMethod) -> bool:
        """
        Test the given challenge response matches the requirements of
        the handler class

        @params  challenge_response  Authentication challenge response (HTTPAuthMethod)
        @return  Match (bool)
        """

    @abstractmethod
    def set_handler_parameters(self, challenge_response: HTTPAuthMethod) -> HTTPValidatorParameters:
        """
        Set the parameters for the authentication challenge response

        @params  challenge_response  Authentication challenge reponse (HTTPAuthMethod)
        @return  Authentication request parameters (HTTPValidatorParameters)
        """

    @abstractmethod
    async def get_authenticated_user(self, challenge_response: HTTPAuthMethod,
                                     auth_response: ClientResponse) -> AuthenticatedUser:
        """
        Get the user from the authentication challenge response and any
        response back from the authentication server

        @params  challenge_response  Authentication challenge response (HTTPAuthMethod)
        @param   auth_response       Response from authentication request (ClientResponse)
        @return  Authenticated user (AuthenticatedUser)
        """

    ####################################################################

    def __init__(self, config: Configuration, logger: Optional[logging.Logger]=None) -> None:
        """
        Constructor

        @param   config  Authentication configuration
        @param   logger  Logger
        """
        super().__init__(logger=logger)
        self._config = config

        # Get the first word of the WWW-Authenticate string
        self._auth_method, *_ = self.www_authenticate.split()

        # Initialise the cache, if required
        if self._config.cache:
            self.log(logging.DEBUG, f"Creating {self._auth_method} authentication cache")
            self._cache: Dict[HTTPAuthMethod, AuthenticatedUser] = {}
            self._cache_lock = Lock()
            self._schedule_cleanup()
            atexit.register(self._cleanup_timer.cancel)

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
            self.log(logging.DEBUG, f"Cleaning {self._auth_method} authentication cache")
            for key, user in list(self._cache.items()):
                if not user.valid(self._config.cache):
                    del self._cache[key]

        self._schedule_cleanup()

    async def _validate_request(self, params: HTTPValidatorParameters) -> Optional[ClientResponse]:
        """
        Asynchronously make an authentication request to check validity

        @param   params  Challenge response validator parameters (HTTPValidatorParameters)
        @return  Authentication response (ClientResponse; None on failure)
        """
        async with ClientSession() as session:
            req_headers = {
                "Authorization": params.payload,
                **params.headers
            }

            async with session.request(params.method, params.url, headers=req_headers) as response:
                if 200 <= response.status < 300:
                    self.log(logging.DEBUG, f"{self._auth_method} authenticated")
                    return response

                if response.status in [401, 403]:
                    self.log(logging.WARNING, f"{self._auth_method} couldn't authenticate")
                else:
                    response.raise_for_status()

        return None

    async def authenticate(self, auth_header: str) -> Optional[AuthenticatedUser]:
        """
        Validate the authorisation header

        @param   auth_header  Contents of the "Authorization" header (string)
        @return  Authenticated user (AuthenticatedUser)
        """
        try:
            _auth_methods = auth_parser(auth_header)
            challenge_response, *_ = filter(self.match_auth_method, _auth_methods)

        except ParseError:
            self.log(logging.WARNING,
                     f"{self._auth_method} authentication handler couldn't parse authentication header")
            return None

        except ValueError:
            self.log(logging.ERROR, f"No HTTP {self._auth_method} authentication handler available")
            return None

        # Check the cache
        if self._config.cache:
            with self._cache_lock:
                if challenge_response in self._cache:
                    user = self._cache[challenge_response]
                    if user.valid(self._config.cache):
                        self.log(logging.DEBUG, f"Authenticated user \"{user.user}\" from cache")
                        return user

                    # Clean up expired users
                    del self._cache[challenge_response]

        auth_response = await self._validate_request(self.set_handler_parameters(challenge_response))
        if auth_response:
            user = await self.get_authenticated_user(challenge_response, auth_response)

            # Put validated user in the cache
            if self._config.cache:
                with self._cache_lock:
                    self._cache[challenge_response] = user

            return user

        return None
