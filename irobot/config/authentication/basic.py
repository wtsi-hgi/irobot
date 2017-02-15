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
from typing import Optional

import requests

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


def _parse_cache(cache:str) -> Optional[float]:
    """
    Parse revalidation cache time := "never"
                                   | NUMERIC TIME_UNIT

    @param   cache  Cache time (string)
    @return  Cache time in seconds (numeric); None for no caching
    """
    if cache.lower() == "never":
        return None

    match = re.match(r"""
        ^(?:
            (?P<value>
                \d+
                (?: \. \d+ )?
            )
            \s*
            (?P<unit>
                (?: s (ec (ond)? s?)? )  # s / sec(s) / second(s)
                |
                (?: m (in (ute)? s?)? )  # m / min(s) / minute(s)
            )
        )$
    """, cache, re.VERBOSE | re.IGNORECASE)

    if not match:
        raise ParsingError("Invalid revalidation cache time")

    multiplier = 60 if match.group("unit").startswith("m") else 1
    value = float(match.group("value")) * multiplier

    # n.b., Zero seconds is the same as "never"
    return value or None


class BasicAuthConfig(BaseConfig):
    """ HTTP basic authentication configuration """
    def __init__(self, url:str, cache:str) -> None:
        """
        Parse HTTP basic authentication configuration

        @param   url    Validation URL (string)
        @param   cache  Cache time for correct validation response (string)
        """
        self._url = _parse_url(url)
        self._cache = _parse_cache(cache)

    def url(self) -> str:
        """
        Get validation URL

        @return  Validation URL (string)
        """
        return self._url

    def cache(self) -> Optional[float]:
        """
        Get revalidation time

        @return  Cache time in seconds (numeric); None for no caching
        """
        return self._cache
