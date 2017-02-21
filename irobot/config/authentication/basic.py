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
from urllib.parse import urlparse

import irobot.common.canon as canon
from irobot.config._base import BaseConfig


def _canon_url(url:str) -> str:
    """
    Canonicalise URL

    @param   url  Validation URL (string)
    @return  Validation URL (string)
    """
    # Prepend http:// if no scheme is specified
    if not re.match(r"^https?://", url):
        url = f"http://{url}"

    components = urlparse(url)

    try:
        _ = canon.ipv4(components.hostname)

    except ValueError:
        try:
            _ = canon.domain_name(components.hostname)

        except ValueError:
            raise ParsingError("Couldn't parse validation URL")

    return url


class BasicAuthConfig(BaseConfig):
    """ HTTP basic authentication configuration """
    def __init__(self, url:str, cache:str) -> None:
        """
        Parse HTTP basic authentication configuration

        @param   url    Validation URL (string)
        @param   cache  Cache invalidation time (string)
        """
        self._url = _canon_url(url)

        try:
            self._cache = canon.duration(cache)
        except ValueError:
            raise ParsingError("Couldn't parse cache invalidation time")

    @property
    def url(self) -> str:
        """
        Get validation URL

        @return  Validation URL (string)
        """
        return self._url

    @property
    def cache(self) -> Optional[timedelta]:
        """
        Get invalidation time

        @return  Cache timeout (timedelta); None for no caching
        """
        return self._cache
