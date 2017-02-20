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

import re
from configparser import ParsingError
from datetime import timedelta
from typing import List, Optional

from irobot.common import parse_ipv4
from irobot.config._base import BaseConfig


def _parse_listening_port(listen:str) -> int:
    """
    Parse listening port

    @param   listen  Listening port (string)
    @return  Listening port (int)
    """
    port = int(listen)

    if not 0 <= port < 2**16:
        raise ParsingError("Listening port number out of range")

    return port


def _parse_timeout(timeout:str) -> Optional[timedelta]:
    """
    Parse response timeout := "unlimited"
                            | INTEGER ["ms"]
                            | NUMBER "s"

    @param   timeout  Response timeout (string)
    @return  Response timeout (timedelta); or None (for unlimited)
    """
    if timeout.lower() == "unlimited":
        return None

    match = re.match(r"""
        ^(?:
            (?:
                (?P<milliseconds> \d+ )
                (?: \s* ms)?
            )
            |
            (?:
                (?P<seconds>
                    \d+
                    (?: \. \d+)?
                )
                \s* s
            )
        )$
    """, timeout, re.VERBOSE)

    if not match:
        raise ParsingError("Invalid timeout")

    if match.group("milliseconds"):
        output = timedelta(milliseconds=int(match.group("milliseconds")))

    if match.group("seconds"):
        output = timedelta(seconds=float(match.group("seconds")))

    # 0 timeout is alias for unlimited
    return output or None


def _parse_authentication(authentication:str) -> List[str]:
    """
    Parse authentication methods := comma-delimited string

    @param   authentication  Authentication methods (string)
    @return  Authentication methods (list of string)
    """
    methods = re.split(r"\s*,\s*", authentication.lower())

    if len(methods) == 1 and methods[0] == "":
        raise ParsingError("Must provide at least one authentication method")

    return methods


class HTTPdConfig(BaseConfig):
    """ HTTPd configuration """
    def __init__(self, bind_address:str, listen:str, timeout:str, authentication:str) -> None:
        """
        Parse HTTPd configuration

        @param   bind_address    IPv4 bind address (string)
        @param   listen          Listening port (string)
        @param   timeout         Response timeout (string)
        @param   authentication  Authentication methods (string)
        """
        try:
            self._bind_address = parse_ipv4(bind_address)
        except ValueError:
            raise ParsingError("Couldn't parse bind address")

        self._listen = _parse_listening_port(listen)
        self._timeout = _parse_timeout(timeout)
        self._authentication = _parse_authentication(authentication)

    def bind_address(self) -> str:
        """
        Get bind address

        @return  IPv4 bind address (string)
        """
        return self._bind_address

    def listen(self) -> int:
        """
        Get listening port

        @return  Listening port (int)
        """
        return self._listen

    def timeout(self) -> Optional[int]:
        """
        Get response timeout

        @return  Response timout in milliseconds (int)
        """
        return self._timeout

    def authentication(self) -> str:
        """
        Get authentication methods

        @return  Authentication methods (list of strings)
        """
        return self._authentication
