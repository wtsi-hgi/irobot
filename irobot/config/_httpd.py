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


def listening_port(listen:str) -> int:
    """
    Canonicalise listening port

    @param   listen  Listening port (string)
    @return  Listening port (int)
    """
    port = int(listen)

    if not 0 <= port < 2**16:
        raise ParsingError("Listening port number out of range")

    return port


def timeout(t:str) -> Optional[timedelta]:
    """
    Canonicalise response timeout string into timedelta

    TIMOUT := "unlimited"
            | INTEGER ["ms"]
            | NUMBER "s"

    @param   t  Response timeout (string)
    @return  Response timeout (timedelta); or None (for unlimited)
    """
    if t.lower() == "unlimited":
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
    """, t, re.VERBOSE)

    if not match:
        raise ParsingError("Invalid timeout")

    if match.group("milliseconds"):
        output = timedelta(milliseconds=int(match.group("milliseconds")))

    if match.group("seconds"):
        output = timedelta(seconds=float(match.group("seconds")))

    # zero timeout is not allowed
    if not output:
        raise ParsingError("Timeout must be greater than zero")

    return output


def authentication(auth:str) -> List[str]:
    """
    Canonicalise comma-delimited authentication methods into list

    @param   auth  Authentication methods (string)
    @return  Authentication methods (list of string)
    """
    methods = re.split(r"\s*,\s*", auth.lower())

    if len(methods) == 1 and methods[0] == "":
        raise ParsingError("Must provide at least one authentication method")

    return methods
