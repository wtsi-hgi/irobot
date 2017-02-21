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
import re
from base64 import b64decode
from typing import Optional, Tuple

from requests import Response, Request

from irobot.authentication._http import HTTPAuthHandler
from irobot.config.authentication import BasicAuthConfig


_BASIC_AUTH_RE = re.compile(r"""
    ^Basic \s
    (
        (?: [a-z0-9+/]{4} )*
        (?: [a-z0-9+/]{2}== | [a-z0-9+/]{3}= )?
    )$
""", re.VERBOSE | re.IGNORECASE)


class HTTPBasicAuthHandler(HTTPAuthHandler):
    """ HTTP basic authentication handler """
    def __init__(self, config:BasicAuthConfig, logger:Optional[logging.Logger] = None) -> None:
        super().__init__(config=config, logger=logger)
        self._auth_re = _BASIC_AUTH_RE

    def parse_auth_header(self, auth_header:str) -> Tuple[str, str]:
        """
        Parse the basic authentication authorisation header

        @param   auth_header  Contents of the "Authorization" header (string)
        @return  Tuple of username (string) and password (string)
        """
        match = self._auth_re.match(auth_header)

        if not match:
            raise ValueError("Invalid HTTP basic authentication header")

        return tuple(b64decode(match.group(1)).decode().split(":"))

    def auth_request(self, user:str, password:str) -> Request:
        """
        Create an authentication request

        @param   user      Username (string)
        @param   password  Password (string)
        @return  Authentication request (requests.Request)
        """
        return Request("GET", self._config.url, auth=(user, password))

    def get_user(self, req:Request, _:Response) -> str:
        """ Get the user from the authentication request """
        return req.auth[0]
