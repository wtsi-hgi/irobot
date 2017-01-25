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
from ConfigParser import ParsingError
from datetime import datetime, timedelta
from types import IntType, FloatType, StringType

from irobot.config._datetime_arithmetic import multiply_timedelta, add_years


def _parse_location(location):
    """
    Parse precache directory location
    @param   location  Precache directory (string)
    @return  Absolute precache directory path (string)
    """
    pass


def _parse_index(index):
    """
    Parse precache tracking database name

    @param   index  Tracking database filename (string)
    @return  Absolute tracking database path (string)
    """
    pass


def _parse_size(size):
    """
    Parse size string

    @param   size  Maximum precache size (string)
    @return  Precache size in bytes (numeric); or None for unlimited
    """
    try:
        assert type(size) is StringType, "Expecting string, not %s" % type(size)
    except AssertionError as e:
        raise TypeError(e.message)

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
    Parse expiry string

    @param   expiry  Maximum file age (string)
    @return  ...
    """
    try:
        assert type(expiry) is StringType, "Expecting string, not %s" % type(expiry)
    except AssertionError as e:
        raise TypeError(e.message)

    pass


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
        try:
            assert type(location) is StringType, "Expecting string, not %s" % type(location)
            assert type(index) is StringType, "Expecting string, not %s" % type(index)
            assert type(size) is StringType, "Expecting string, not %s" % type(size)
            assert type(expiry) is StringType, "Expecting string, not %s" % type(expiry)
        except AssertionError as e:
            raise TypeError(e.message)

        self._location = _parse_location(location)
        self._index = _parse_index(index)
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
        try:
            assert isinstance(from_atime, datetime), "Expecting datetime, not %s" % type(from_atime)
        except AssertionError as e:
            raise TypeError(e.message)

        if not self._expiry:
            # Unlimited
            return None

        if isinstance(self._expiry, timedelta):
            # +timedelta
            return from_atime + self._expiry

        if type(self._expiry) in [IntType, FloatType]:
            # +x years
            return add_years(from_atime, self._expiry)
