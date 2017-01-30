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
from ConfigParser import ParsingError
from types import StringType

from irobot.common import type_check


def _parse_bind_address(bind_address):
    """
    Parse bind address

    @param   bind_address  IPv4 bind address (string)
    @return  IPv4 bind address in dotted decimal (string)
    """
    type_check(bind_address, StringType)

    match = re.match(r"""
        ^(?:
            (?P<dotted_dec>                 # e.g., 222.173.190.239
                \d{1,3}
                (?: \. \d{1,3} ){3}
            )
            |
            (?P<decimal>                    # e.g., 3735928559
                \d +
            )
            |
            (?P<hex>                        # e.g., 0xdeadbeef
                0x [0-9a-f]+
            )
            |
            (?P<dotted_hex>                 # e.g., 0xde.0xad.0xbe.0xef
                0x [0-9a-f]{2}
                (?: \. 0x [0-9a-f]{2} ){3}
            )
            |
            (?P<dotted_oct>                 # e.g., 0336.0255.0276.0357
                0 [0-7]{3}
                (?: \. 0 [0-7]{3} ){3}
            )
        )$
    """, bind_address, re.VERBOSE | re.IGNORECASE)

    if not match:
        raise ParsingError("Invalid IPv4 address")

    # Dotted address
    if match.group("dotted_dec") or match.group("dotted_hex") or match.group("dotted_oct"):
        parts = []

        address = match.group("dotted_dec") or \
                  match.group("dotted_hex") or \
                  match.group("dotted_oct")

        base = 10 if match.group("dotted_dec") else \
               16 if match.group("dotted_hex") else \
                8

        for part in address.split("."):
            int_part = int(part, base)

            if not 0 <= int_part < 256:
                raise ParsingError("Invalid IPv4 address")

            parts.append(int_part)

    # Plain address
    if match.group("decimal") or match.group("hex"):
        base = 10 if match.group("decimal") else 16
        value = int(match.group("decimal") or match.group("hex"), base)

        if not 0 <= value < 2**32:
            raise ParsingError("IPv4 address out of range")

        parts = [
            (value & 0xff000000) >> 24,
            (value & 0xff0000) >> 16,
            (value & 0xff00) >> 8,
            value & 0xff
        ]

    return ".".join(str(part) for part in parts)


def _parse_listening_port(listen):
    """
    Parse listening port

    @param   listen  Listening port (string)
    @return  Listening port (int)
    """
    type_check(listen, StringType)
    port = int(listen)

    if not 0 <= port < 2**16:
        raise ParsingError("Listening port number out of range")

    return port


class HTTPdConfig(object):
    """ HTTPd configuration """
    def __init__(self, bind_address, listen):
        """
        Parse HTTPd configuration

        @param   bind_address  IPv4 bind address (string)
        @param   listen        Listening port (string)
        """
        type_check(bind_address, StringType)
        type_check(listen, StringType)

        self._bind_address = _parse_bind_address(bind_address)
        self._listen = _parse_listening_port(listen)

    def bind_address(self):
        """
        Get bind address

        @return  IPv4 bind address (string)
        """
        return self._bind_address

    def listen(self):
        """
        Get listening port

        @return  Listening port (int)
        """
        return self._listen
