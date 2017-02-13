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
from types import NoneType, ObjectType, StringType, TypeType

from irobot.common import canonical_path, type_check_arguments, type_check_return
from irobot.config._base import BaseConfig
from irobot.config.httpd import HTTPdConfig
from irobot.config.irods import iRODSConfig
from irobot.config.log import LoggingConfig
from irobot.config.precache import PrecacheConfig
from irobot.config.authentication import ArvadosAuthConfig, BasicAuthConfig


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
HTTPD_TIMEOUT = "timeout"
HTTPD_AUTHENTICATION = "authentication"

AUTH_BASIC = "basic_auth"
AUTH_BASIC_URL = "url"

AUTH_ARVADOS = "arvados_auth"

AUTH_HANDLERS = {
    AUTH_BASIC: {
        "constructor": BasicAuthConfig,
        "options": (AUTH_BASIC_URL,)
    },
    AUTH_ARVADOS: {
        "constructor": ArvadosAuthConfig,
        "options": ()
    }
}

LOGGING = "logging"
LOGGING_OUTPUT = "output"
LOGGING_LEVEL = "level"


class _AuthHandlers(object):
    """ Authentication handler configuration container """
    @type_check_arguments(handlers=BaseConfig)
    def __init__(self, **handlers):
        for name, handler in handlers.items():
            setattr(self, name, handler)


class Configuration(object):
    """ iRobot configuration """
    @type_check_arguments(config_file=StringType)
    def __init__(self, config_file):
        """
        Open and parse configuration from file

        @param   config_file  Configuration filename
        """
        self.config = ConfigParser()
        self.file = canonical_path(config_file)

        with open(self.file, "r") as fp:
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
                                                            HTTPD_LISTEN,
                                                            HTTPD_TIMEOUT,
                                                            HTTPD_AUTHENTICATION)
        
        # Build authentication handler configurations
        try:
            self.authentication = _AuthHandlers(**{
                handler: self._build_config(
                    AUTH_HANDLERS["%s_auth" % handler]["constructor"],
                    "%s_auth" % handler,
                    *AUTH_HANDLERS["%s_auth" % handler]["options"]
                )
                for handler in self.httpd.authentication()
            })

        except KeyError as e:
            auth_method = re.search(r"^(\w+)_auth$", e.message).group(1)
            raise ParsingError("No such authentication method \"%s\"" % auth_method)

        # Build logging configuration
        self.logging = self._build_config(LoggingConfig, LOGGING, LOGGING_OUTPUT,
                                                                  LOGGING_LEVEL)

    @type_check_return(BaseConfig)
    def get_sections(self):
        """
        Get instantiated configurations

        @return  Configurations (dictionary of objects inheriting BaseConfig)
        """
        return {
            config: getattr(self, config)
            for config in dir(self)
            if isinstance(getattr(self, config), BaseConfig)
        }

    @type_check_return(BaseConfig)
    @type_check_arguments(constructor=BaseConfig.__class__, section=StringType)
    def _build_config(self, constructor, section, *options):
        """
        Build configuration

        @param   constructor  Configuration class (class inheriting BaseConfig)
        @param   section      Section (string)
        @param   *options     Options (strings)

        @return  Instantiated configuration (object inheriting BaseConfig)
        """
        return constructor(**{
            k:self.config.get(section, k)
            for k in options
        })
