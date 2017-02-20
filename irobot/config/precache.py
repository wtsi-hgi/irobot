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

import os
import re
from configparser import ParsingError
from datetime import datetime, timedelta
from numbers import Number
from typing import Optional, Union

import irobot.common.canon as canon
from irobot.common import add_years
from irobot.config._base import BaseConfig


def _canon_location(location:str) -> str:
    """
    Canonicalise precache directory location

    @param   location  Precache directory (string)
    @return  Absolute precache directory path (string)
    """
    return canon.path(location)


def _canon_index(location:str, index:str) -> str:
    """
    Canonicalise precache tracking database name

    @param   location  Precache directory (string)
    @param   index     Tracking database filename (string)
    @return  Absolute tracking database path (string)
    """
    dirname, basename = os.path.split(index)

    if basename == "":
        raise ParsingError("Precache index must be a filename")

    if dirname == "" and basename == index:
        return os.path.join(location, index)

    return os.path.join(canon.path(dirname), basename)


def _canon_limited_size(size:str) -> int:
    """
    Canonicalise human size string to bytes

    @param   size  File size, optionally suffixed (string)
    @return  Size in bytes (int)
    """
    try:
        return canon.human_size(size)

    except ValueError:
        raise ParsingError("Could not parse file size configuration")


def _canon_unlimited_size(size:str) -> Optional[int]:
    """
    Canonicalise optionally unlimited human size string to bytes

    @param   size  File size, optionally suffixed (string)
    @return  Size in bytes (int); or None for unlimited
    """
    if size.lower() == "unlimited":
        return None

    return _canon_limited_size(size)


def _canon_expiry(expiry:str) -> Union[timedelta, Number, None]:
    """
    Canonicalise cache invalidation expiry string

    EXPIRY := "unlimited"
            | NUMBER ( "h" | "hour" ["s"]
                     | "d" | "day"  ["s"]
                     | "w" | "week" ["s"]
                     | "y" | "year" ["s"] )

    @param   expiry  Maximum file age (string)
    @return  None for unlimited; an absolute difference (timedelta); or
             a number of years (numeric)
    """
    if expiry.lower() == "unlimited":
        return None

    match = re.match(r"""
        ^                     # Anchor to start of string
        (?P<quantity>
            \d+               # Integer or floating point number into
            (?: \. \d+ )?     # "quantity" group
        )
        \s*
        (?P<unit>             # Into "unit" group:
            h (?: our s?)? |  # * Hours 
            d (?: ay s?)?  |  # * Days
            w (?: eek s?)? |  # * Weeks
            y (?: ear s?)?    # * Years
        )
        $
    """, expiry, re.VERBOSE | re.IGNORECASE)

    if not match:
        raise ParsingError("Could not parse precache expiry configuration")

    val = float(match.group('quantity'))
    unit = match.group('unit')[0].lower()  # First character (lowercase)

    # Years
    if unit == "y":
        return val

    # Hours, Days or Weeks
    return val * {
        "h": timedelta(hours = 1),
        "d": timedelta(days  = 1),
        "w": timedelta(weeks = 1)
    }[unit]


class PrecacheConfig(BaseConfig):
    """ Precache configuration """
    def __init__(self, location:str, index:str, size:str, expiry:str, chunk_size:str) -> None:
        """
        Parse precache configuration

        @param   location    Precache directory (string)
        @param   index       Tracking database filename (string)
        @param   size        Maximum precache size (string)
        @param   expiry      Maximum file age (string)
        @param   chunk_size  File block size for checksumming (string)
        """
        self._location = _canon_location(location)
        self._index = _canon_index(self._location, index)
        self._size = _canon_unlimited_size(size)
        self._expiry = _canon_expiry(expiry)
        self._chunk_size = _canon_limited_size(chunk_size)

    def __str__(self) -> None:
        if self._expiry is None:
            expiry = "unlimited"

        elif isinstance(self._expiry, timedelta):
            expiry = str(self._expiry)

        else:
            expiry = f"{self._expiry} years"

        return str({
            "location": self._location,
            "index": self._index,
            "size": self._size or "unlimited",
            "expiry": expiry,
            "chunk_size": self._chunk_size
        }).replace("'", "")

    def location(self) -> str:
        """
        Get precache directory

        @return  Precache directory (string)
        """
        return self._location

    def index(self) -> str:
        """
        Get precache tracking database filename

        @return  Precache tracking database filename (string)
        """
        return self._index

    def size(self) -> Optional[int]:
        """
        Get precache size

        @return  Precache size in bytes (numeric); or None for unlimited
        """
        return self._size

    def expiry(self, from_atime:datetime) -> Optional[datetime]:
        """
        Get file expiration based on lasted access time

        @param   from_atime  Basis access time (datetime)
        @return  Expiry timestamp (datetime); or None for unlimited
        """
        if not self._expiry:
            # Unlimited
            return None

        if isinstance(self._expiry, timedelta):
            # +timedelta
            return from_atime + self._expiry

        if isinstance(self._expiry, Number):
            # +x years
            return add_years(from_atime, self._expiry)

    def chunk_size(self) -> int:
        """
        Get file chunking size for checksumming

        @return  Chunk size in bytes (int)
        """
        return self._chunk_size
