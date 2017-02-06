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
from ConfigParser import ParsingError
from datetime import datetime, timedelta
from types import FloatType, IntType, NoneType, StringType

from irobot.common import (add_years, canonical_path, multiply_timedelta,
                           parse_human_size, type_check,
                           type_check_return)


@type_check_return(StringType)
def _parse_location(location):
    """
    Parse precache directory location
    @param   location  Precache directory (string)
    @return  Absolute precache directory path (string)
    """
    type_check(location, StringType)
    return canonical_path(location)


@type_check_return(StringType)
def _parse_index(location, index):
    """
    Parse precache tracking database name

    @param   location  Precache directory (string)
    @param   index     Tracking database filename (string)
    @return  Absolute tracking database path (string)
    """
    type_check(location, StringType)
    type_check(index, StringType)

    dirname, basename = os.path.split(index)

    if basename == "":
        raise ParsingError("Precache index must be a filename")

    if dirname == "" and basename == index:
        return os.path.join(location, index)

    return os.path.join(canonical_path(dirname), basename)


@type_check_return(IntType)
def _parse_limited_size(size):
    """
    Parse size string := HUMAN-SIZE

    @param   size  File size, optionally suffixed (string)
    @return  Size in bytes (int)
    """
    type_check(size, StringType)

    try:
        return parse_human_size(size)

    except ValueError:
        raise ParsingError("Could not parse file size configuration")


@type_check_return(IntType, NoneType)
def _parse_unlimited_size(size):
    """
    Parse size string := "unlimited"
                       | HUMAN-SIZE

    @param   size  File size, optionally suffixed (string)
    @return  Size in bytes (int); or None for unlimited
    """
    type_check(size, StringType)

    if size.lower() == "unlimited":
        return None

    return _parse_limited_size(size)


@type_check_return(NoneType, timedelta, IntType, FloatType)
def _parse_expiry(expiry):
    """
    Parse expiry string := "unlimited"
                         | NUMBER ( "h" | "hour" | "hours"
                                  | "d" | "day"  | "days"
                                  | "w" | "week" | "weeks"
                                  | "y" | "year" | "years" )

    @param   expiry  Maximum file age (string)
    @return  None for unlimited; an absolute difference (timedelta); or
             a number of years (numeric)
    """
    type_check(expiry, StringType)

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
    return multiply_timedelta({
        "h": timedelta(hours = 1),
        "d": timedelta(days  = 1),
        "w": timedelta(weeks = 1)
    }[unit], val)


class PrecacheConfig(object):
    """ Precache configuration """
    def __init__(self, location, index, size, expiry, chunk_size):
        """
        Parse precache configuration

        @param   location    Precache directory (string)
        @param   index       Tracking database filename (string)
        @param   size        Maximum precache size (string)
        @param   expiry      Maximum file age (string)
        @param   chunk_size  File block size for checksumming (string)
        """
        type_check(location, StringType)
        type_check(index, StringType)
        type_check(size, StringType)
        type_check(expiry, StringType)
        type_check(chunk_size, StringType)

        self._location = _parse_location(location)
        self._index = _parse_index(self._location, index)
        self._size = _parse_unlimited_size(size)
        self._expiry = _parse_expiry(expiry)
        self._chunk_size = _parse_limited_size(chunk_size)

    @type_check_return(StringType)
    def location(self):
        """
        Get precache directory

        @return  Precache directory (string)
        """
        return self._location

    @type_check_return(StringType)
    def index(self):
        """
        Get precache tracking database filename

        @return  Precache tracking database filename (string)
        """
        return self._index

    @type_check_return(IntType, NoneType)
    def size(self):
        """
        Get precache size

        @return  Precache size in bytes (numeric); or None for unlimited
        """
        return self._size

    @type_check_return(NoneType, datetime)
    def expiry(self, from_atime):
        """
        Get file expiration based on lasted access time

        @param   from_atime  Basis access time (datetime)
        @return  Expiry timestamp (datetime); or None for unlimited
        """
        type_check(from_atime, datetime)

        if not self._expiry:
            # Unlimited
            return None

        if isinstance(self._expiry, timedelta):
            # +timedelta
            return from_atime + self._expiry

        if type(self._expiry) in [IntType, FloatType]:
            # +x years
            return add_years(from_atime, self._expiry)

    @type_check_return(IntType)
    def chunk_size(self):
        """
        Get file chunking size for checksumming

        @return  Chunk size in bytes (int)
        """
        return self._chunk_size
