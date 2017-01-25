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

from ConfigParser import ConfigParser
from types import StringType

from irobot.common import type_check
from irobot.config._precache import PrecacheConfig


PRECACHE = "precache"
PRECACHE_LOCATION = "location"
PRECACHE_INDEX = "index"
PRECACHE_SIZE = "size"
PRECACHE_EXPIRY = "expiry"

IRODS = "irods"
IRODS_MAX_CONNECTIONS = "max_connections"


class Configuration(object):
    """ iRobot configuration """
    def __init__(self, config_file):
        """
        Open and parse configuration from file

        @param   config_file  Configuration filename
        """
        type_check(config_file, StringType)

        config = ConfigParser()

        with open(config_file, "r") as fp:
            config.readfp(fp)

        # Build precache configuration
        self.precache = PrecacheConfig(**{
            k:config.get(PRECACHE, k)
            for k in [PRECACHE_LOCATION,
                      PRECACHE_INDEX,
                      PRECACHE_SIZE,
                      PRECACHE_EXPIRY]
        })
