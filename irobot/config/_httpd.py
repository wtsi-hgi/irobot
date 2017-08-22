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

from irobot.config._tree_builder import Configuration


def listening_port(value:str) -> int:
    """
    Canonicalise listening port

    @param   value  Listening port (string)
    @return  Listening port (int)
    """
    port = int(value)

    if not 0 <= port < 2**16:
        raise ParsingError("Listening port number out of range")

    return port


def timeout(value:str) -> Optional[timedelta]:
    """
    Canonicalise response timeout string into timedelta

    TIMOUT := "unlimited"
            | INTEGER ["ms"]
            | NUMBER "s"

    @param   value  Response timeout (string)
    @return  Response timeout (timedelta); or None (for unlimited)
    """
    if value.lower() == "unlimited":
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
    """, value, re.VERBOSE)

    if not match:
        raise ParsingError("Invalid timeout")

    if match["milliseconds"]:
        output = timedelta(milliseconds=int(match["milliseconds"]))

    if match["seconds"]:
        output = timedelta(seconds=float(match["seconds"]))

    # zero timeout is not allowed
    if not output:
        raise ParsingError("Timeout must be greater than zero")

    return output


def authentication(value:str) -> List[str]:
    """
    Canonicalise comma-delimited authentication methods into list

    @param   value  Authentication methods (string)
    @return  Authentication methods (list of string)
    """
    methods = re.split(r"\s*,\s*", value.lower())

    if len(methods) == 1 and methods[0] == "":
        raise ParsingError("Must provide at least one authentication method")

    return methods


class HTTPdConfig(Configuration):
    """ HTTPd configuration stub """
