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
from typing import Optional, Tuple

from requests import Response, Request

from irobot.authentication._http import HTTPAuthHandler
from irobot.config import ArvadosAuthConfig


# TODO Write a parser to decode Bearer authentication
_ARV_AUTH_RE =  re.compile(r"""
    ^Arvados \s
    ( .+ )$
""", re.VERBOSE | re.IGNORECASE)


class ArvadosAuthHandler(HTTPAuthHandler):
    """ Arvados authentication handler """
    def __init__(self, config:ArvadosAuthConfig, logger:Optional[logging.Logger] = None) -> None:
        super().__init__(config=config, logger=logger)
        self._auth_re = _ARV_AUTH_RE

    @property
    def www_authenticate(self) -> str:
        return f"Bearer realm=\"{self._config.api_host}\""

    def parse_auth_header(self, auth_header:str) -> Tuple[str]:
        """
        Parse the Arvados authentication authorisation header

        @param   auth_header  Contents of the "Authorization" header (string)
        @return  Arvados API token (1-tuple of string)
        """
        match = self._auth_re.match(auth_header)

        if not match:
            raise ValueError("Invalid Arvados authentication header")

        return match.group(1),

    def auth_request(self, api_token:str) -> Request:
        """
        Create an authentication request

        @param   api_token  Arvados API token (string)
        @return  Authentication request (requests.Request)
        """
        if self._config.api_version == "v1":
            return Request("GET", f"{self._config.api_base_url}/users/current", headers={
               "Authorization": f"OAuth2 {api_token}",
               "Accept": "application/json"
            })

    def get_user(self, _:Request, res:Response) -> str:
        """ Get the user from the authentication response """
        if res.status_code == 200:
            return res.json()["username"]

        raise ValueError("Could not retrieve username from Arvados API host")
