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
from types import ObjectType, StringType, TypeType

from irobot.common import canonical_path, type_check, type_check_collection, type_check_return
from irobot.config.httpd import HTTPdConfig
from irobot.config.irods import iRODSConfig
from irobot.config.misc import MiscConfig
from irobot.config.precache import PrecacheConfig


PRECACHE = "precache"
PRECACHE_LOCATION = "location"
PRECACHE_INDEX = "index"
PRECACHE_SIZE = "size"
PRECACHE_EXPIRY = "expiry"
PRECACHE_CHUNK_SIZE = "chunk_size"

IRODS = "irods"
IRODS_MAX_CONNECTIONS = "max_connections"

HTTPD = "httpd"
HTTPD_BIND_ADDRESS = "bind_address"
HTTPD_LISTEN = "listen"

MISC = "misc"
MISC_LOG_LEVEL = "log_level"


class Configuration(object):
    """ iRobot configuration """
    def __init__(self, config_file):
        """
        Open and parse configuration from file

        @param   config_file  Configuration filename
        """
        type_check(config_file, StringType)

        self.config = ConfigParser()

        with open(canonical_path(config_file), "r") as fp:
            self.config.readfp(fp)

        # Build precache configuration
        self.precache = self._build_config(PrecacheConfig, PRECACHE, PRECACHE_LOCATION,
                                                                     PRECACHE_INDEX,
                                                                     PRECACHE_SIZE,
                                                                     PRECACHE_EXPIRY,
                                                                     PRECACHE_CHUNK_SIZE)
        # Build iRODS configuration
        self.irods = self._build_config(iRODSConfig, IRODS, IRODS_MAX_CONNECTIONS)

        # Build HTTPd configuration
        self.httpd = self._build_config(HTTPdConfig, HTTPD, HTTPD_BIND_ADDRESS,
                                                            HTTPD_LISTEN)

        # Build miscellaneous configuration
        self.misc = self._build_config(MiscConfig, MISC, MISC_LOG_LEVEL)

    @type_check_return(ObjectType)
    def _build_config(self, constructor, section, *options):
        """
        Build configuration

        @param   constructor  Configuration class (class)
        @param   section      Section (string)
        @param   *options     Options (strings)

        @return  Instantiated configuration (object)
        """
        type_check(constructor, TypeType)
        type_check(section, StringType)
        type_check_collection(options, StringType)

        return constructor(**{
            k:self.config.get(section, k)
            for k in options
        })
