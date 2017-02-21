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
from typing import Optional

from irobot.authentication._http import HTTPAuthHandler
from irobot.config.authentication import ArvadosAuthConfig


_ARV_AUTH_RE =  re.compile(r"""
    ^Arvados \s
    ( .+ )$
""", re.VERBOSE | re.IGNORECASE)


class ArvadosAuthHandler(HTTPAuthHandler):
    """ Arvados authentication handler """
    def __init__(self, config:ArvadosAuthConfig, logger:Optional[logging.Logger] = None) -> None:
        super().__init__(config=config, logger=logger)
        self._auth_re = _ARV_AUTH_RE

    def parse_auth_header(self, auth_header:str) -> str:
        """
        Parse the Arvados authentication authorisation header

        @param   auth_header  Contents of the "Authorization" header (string)
        @return  Arvados API token (string)
        """
        match = self._auth_re.match(auth_header)

        if not match:
            raise ValueError("Invalid Arvados authentication header")

        return match.group(1)

    def authenticate(self, auth_header:str) -> bool:
        """
        Validate the authorisation header

        @param   auth_header  Contents of the "Authorization" header (string)
        @return  Validation success (boolean)
        """

        # TODO
        pass
