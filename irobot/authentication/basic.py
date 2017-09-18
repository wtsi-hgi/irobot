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
from base64 import b64decode
from typing import Optional

from aiohttp import ClientResponse

from irobot.authentication._base import AuthenticatedUser
from irobot.authentication._http import BaseHTTPAuthHandler, HTTPValidatorParameters
from irobot.authentication.parser import HTTPAuthMethod
from irobot.config import BasicAuthConfig


class HTTPBasicAuthHandler(BaseHTTPAuthHandler):
    """ HTTP basic authentication handler """
    _challenge:str

    def __init__(self, config:BasicAuthConfig, logger:Optional[logging.Logger] = None) -> None:
        super().__init__(config=config, logger=logger)

        self._challenge = "Basic"
        if self._config.realm:
            self._challenge += f" realm=\"{self._config.realm}\""

    @property
    def www_authenticate(self) -> str:
        return self._challenge

    def match_auth_method(self, challenge_response:HTTPAuthMethod) -> bool:
        return challenge_response.auth_method == "Basic" \
           and challenge_response.payload is not None

    def set_handler_parameters(self, challenge_response:HTTPAuthMethod) -> HTTPValidatorParameters:
        return HTTPValidatorParameters(
            url=self._config.url,
            payload=str(challenge_response)
        )

    def get_authenticated_user(self, challenge_response:HTTPAuthMethod, _:ClientResponse) -> AuthenticatedUser:
        username, _ = b64decode(challenge_response.payload).decode().split(":")
        return AuthenticatedUser(username)
