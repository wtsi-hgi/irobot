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

import requests

from irobot.common import parse_duration
from irobot.config._base import BaseConfig


def _parse_url(url:str) -> str:
    """
    Check validation URL is accepting connections

    @param   url  Validation URL (string)
    @return  Validation URL (string)
    """
    try:
        # Prepend "http://" if it doesn't exist
        if not re.match(r"^https?://", url):
            url = "http://" + url

        # FIXME? Is this a reasonable thing to do?
        requests.head(url, timeout=0.25)

    except requests.Timeout:
        raise ParsingError(f"Didn't receive a response from {url} in a reasonable amount of time")

    except Exception:
        raise ParsingError(f"Couldn't connect to {url}")

    return url


class BasicAuthConfig(BaseConfig):
    """ HTTP basic authentication configuration """
    def __init__(self, url:str, cache:str) -> None:
        """
        Parse HTTP basic authentication configuration

        @param   url    Validation URL (string)
        @param   cache  Cache invalidation time (string)
        """
        self._url = _parse_url(url)

        try:
            self._cache = parse_duration(cache)
        except ValueError:
            raise ParsingError("Couldn't parse cache invalidation time")

    def url(self) -> str:
        """
        Get validation URL

        @return  Validation URL (string)
        """
        return self._url

    def cache(self) -> Optional[timedelta]:
        """
        Get invalidation time

        @return  Cache timeout (timedelta); None for no caching
        """
        return self._cache
