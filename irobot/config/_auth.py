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
from urllib.parse import urlparse

import irobot.common.canon as canon


def url(value:str) -> str:
    """
    Canonicalise URL

    @param   value  Validation URL (string)
    @return  Validation URL (string)
    """
    # Prepend http:// if no scheme is specified
    if not re.match(r"^https?://", value):
        value = f"http://{value}"

    components = urlparse(value)

    try:
        _ = canon.ipv4(components.hostname)

    except ValueError:
        try:
            _ = canon.domain_name(components.hostname)

        except ValueError:
            raise ParsingError("Couldn't parse validation URL")

    return value


def arvados_hostname(value:str) -> str:
    """
    Canonicalise API hostname

    @param   value  Arvados API host
    @return  Canonicalised hostname
    """
    try:
        return canon.ipv4(value)

    except ValueError:
        try:
            return canon.domain_name(value)

        except ValueError:
            raise ParsingError("Couldn't parse API host")


def arvados_version(value:str) -> str:
    """
    Canonicalise API version

    @param   value  Arvados API version
    @return  Canonicalised version
    """
    allowed = ["v1"]

    if value in allowed:
        return value

    raise ParsingError("Unknown Arvados API version")
