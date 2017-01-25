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
import os.path
from ConfigParser import ParsingError
from datetime import datetime, timedelta
from types import IntType, FloatType, StringType

from irobot.common import type_check, multiply_timedelta, add_years


def _parse_location(location):
    """
    Parse precache directory location
    @param   location  Precache directory (string)
    @return  Absolute precache directory path (string)
    """
    type_check(location, StringType)
    # TODO


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

    dirname = os.path.abspath(os.path.expanduser(dirname))
    return os.path.join(dirname, basename)


def _parse_size(size):
    """
    Parse size string := "unlimited"
                       | INTEGER ["B"]
                       | NUMBER ("k" | "M" | "G" | "T") ["i"] "B"

    @param   size  Maximum precache size (string)
    @return  Precache size in bytes (numeric); or None for unlimited
    """
    type_check(size, StringType)

    if size.lower() == "unlimited":
        return None

    match = re.match(r"""
        ^(?:                       # Anchor to start of string
            (?:
                (?P<bytes> \d+ )   # One or more digits into "bytes" group
                (?: \s* B )?       # ...optionally followed by suffix
            )
            |                      # OR
            (?:
                (?P<quantity>
                    \d+            # Integer or floating point number
                    (?: \. \d+ )?  # into "quantity" group
                )
                \s*
                (?P<multiplier>    # Into "multiplier" group:
                    ki? |          # * Kilo or kibibytes
                    Mi? |          # * Mega or mebibytes
                    Gi? |          # * Giga or gibibytes
                    Ti?            # * Tera or tibibytes
                )
                B
            )
        )$                         # Anchor to end of string
    """, size, re.VERBOSE)

    if not match:
        raise ParsingError("Could not parse precache size configuration")

    if match.group('bytes'):
        # Whole number of bytes
        return int(match.group('bytes'))

    if match.group('quantity'):
        # Suffixed multiplier
        size = float(match.group('quantity'))
        multipliers = {
            'k': 1000,    'ki': 1024,
            'M': 1000**2, 'Mi': 1024**2,
            'G': 1000**3, 'Gi': 1024**3,
            'T': 1000**4, 'Ti': 1024**4
        }

        return int(size * multipliers[match.group('multiplier')])


def _parse_expiry(expiry):
    """
    Parse expiry string := "unlimited"
                        |  NUMBER ( "h" | "hour" | "hours"
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
    def __init__(self, location, index, size, expiry):
        """
        Parse precache configuration

        @param   location  Precache directory (string)
        @param   index     Tracking database filename (string)
        @param   size      Maximum precache size (string)
        @param   expiry    Maximum file age (string)
        """
        type_check(location, StringType)
        type_check(index, StringType)
        type_check(size, StringType)
        type_check(expiry, StringType)

        self._location = _parse_location(location)
        self._index = _parse_index(self._location, index)
        self._size = _parse_size(size)
        self._expiry = _parse_expiry(expiry)

    def location(self):
        """
        Get precache directory

        @return  Precache directory (string)
        """
        return self._location

    def index(self):
        """
        Get precache tracking database filename

        @return  Precache tracking database filename (string)
        """
        return self._index

    def size(self):
        """
        Get precache size

        @return  Precache size in bytes (numeric); or None for unlimited
        """
        return self._size

    def expiry(self, from_atime):
        """
        Get file expiration based on lasted access time

        @param   from_atime  Basis access time (datetime)
        @return  Expiry timestamp (datetime)
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
