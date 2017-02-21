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
from typing import Optional

import irobot.common.canon as canon
from irobot.config._base import BaseConfig


def _canon_hostname(api_host:str) -> str:
    """
    Canonicalise API hostname

    @param   api_host  Arvados API host
    @return  Canonicalised hostname
    """
    try:
        return canon.ipv4(api_host)

    except ValueError:
        try:
            return canon.domain_name(api_host)

        except ValueError:
            raise ParsingError("Couldn't parse API host")


def _canon_version(api_version:str) -> str:
    """
    Canonicalise API version

    @param   api_version  Arvados API version
    @return  Canonicalised version
    """
    allowed = ["v1"]

    if api_version in allowed:
        return api_version

    raise ParsingError("Unknown Arvados API version")


class ArvadosAuthConfig(BaseConfig):
    """ Arvados authentication configuration """
    def __init__(self, api_host:str, api_version:str, cache:str) -> None:
        """
        Parse Arvados authentication configuration

        @param   api_host  Arvados API host
        @param   cache     Cache invalidation time (string)
        """
        self._api_host = _canon_hostname(api_host)
        self._api_version = _canon_version(api_version)

        try:
            self._cache = canon.duration(cache)
        except ValueError:
            raise ParsingError("Couldn't parse cache invalidation time")

    @property
    def api_host(self) -> str:
        """
        Get Arvados API host

        @return  Arvados API host (string)
        """
        return self._api_host

    @property
    def api_version(self) -> str:
        """
        Get Arvados API version

        @return  Arvados API version (string)
        """
        return self._api_version

    @property
    def api_base_url(self) -> str:
        """
        Get the Arvados API base URL

        @return  Arvados API base URL (string)
        """
        if self._api_version == "v1":
            return f"https://{self._api_host}/arvados/v1"

    @property
    def cache(self) -> Optional[timedelta]:
        """
        Get invalidation time

        @return  Cache timeout (timedelta); None for no caching
        """
        return self._cache
