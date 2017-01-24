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
from ConfigParser import ConfigParser, ParsingError
from datetime import datetime, timedelta

#import irobot.config._consts as CONFIG
from irobot.config._datetime_arithmetic import multiply_timedelta, add_years


class _PrecacheConfig(object):
    """ Precache configuration """
    def __init__(self, size, expiry):
        """
        Parse precache configuration

        @param   size    Maximum precache size (string)
        @param   expiry  Maximum file age (string)
        """
        self._size = _PrecacheConfig._parse_size(size)
        self._expiry = _PrecacheConfig._parse_expiry(expiry)

    @staticmethod
    def _parse_size(size):
        """
        Parse size string

        @param   size  Maximum precache size (string)
        @return  Precache size in bytes (numeric); or None for unlimited
        """
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

    @staticmethod
    def _parse_expiry(expiry):
        """
        Parse expiry string

        @param   expiry  Maximum file age (string)
        @return  ...
        """
        pass

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
        return self._expiry(from_atime)


class Configuration(object):
    """ iRobot configuration """
    def __init__(self, config_file):
        """
        Open and parse configuration from file

        @param   config_file  Configuration filename
        """
        config = ConfigParser()

        with open(config_file, "r") as fp:
            config.readfp(fp)

        # Build precache configuration
        size = config.get(CONFIG.PRECACHE, CONFIG.PRECACHE_SIZE)
        expiry = config.get(CONFIG.PRECACHE, CONFIG.PRECACHE_EXPIRY)
        self.precache = _PrecacheConfig(size, expiry)
