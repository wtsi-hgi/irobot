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

from configparser import ConfigParser, ParsingError
from functools import partial
from typing import Callable, Dict, Type

import irobot.common.canon as canon
from irobot.config import _auth as auth
from irobot.config import _httpd as httpd
from irobot.config import _irods as irods
from irobot.config import _log as log
from irobot.config import _precache as precache
from irobot.config._tree_builder import ConfigValue, Configuration, OptionalKey, RequiredKey, config_factory


class _ConfigFactories(object):
    def __init__(self) -> None:
        self._factories: Dict[str, Callable[[ConfigParser], Configuration]] = {}

    def add(self, section: str, constructor: Type[Configuration], *mappings):
        self._factories[section] = lambda config: config_factory(constructor, config, section, *mappings)

    def __call__(self, section: str, config: ConfigParser) -> Configuration:
        return self._factories[section](config)


_factories = _ConfigFactories()

_factories.add("precache", precache.PrecacheConfig,
    RequiredKey("location",        canon.path),
    # "index" is dependent upon "location", so we add it later...
    RequiredKey("size",            precache.unlimited_size),
    OptionalKey("age_threshold",   precache.age_threshold),
    RequiredKey("expiry",          precache.expiry),
    RequiredKey("chunk_size",      precache.limited_size)
)

_factories.add("irods", irods.iRODSConfig,
    RequiredKey("max_connections", irods.max_connections)
)

_factories.add("httpd", httpd.HTTPdConfig,
    RequiredKey("bind_address",    canon.ipv4),
    RequiredKey("listen",          httpd.listening_port),
    RequiredKey("timeout",         httpd.timeout),
    RequiredKey("authentication",  httpd.authentication)
)

_factories.add("basic_auth", auth.BasicAuthConfig,
    RequiredKey("url",             auth.url),
    RequiredKey("cache",           canon.duration),
    OptionalKey("realm",           canon.free_text)
)

_factories.add("arvados_auth", auth.ArvadosAuthConfig,
    RequiredKey("api_host",        auth.arvados_hostname),
    RequiredKey("api_version",     auth.arvados_version),
    # "api_base_url" is dependent upon "api_host" and "api_version", so we add it later...
    RequiredKey("cache",           canon.duration)
)

_factories.add("logging", log.LoggingConfig,
    RequiredKey("output",          log.output),
    RequiredKey("level",           log.level)
)


class iRobotConfiguration(Configuration):
    """ Top-level iRobot configuration """
    def __init__(self, config_file: str) -> None:
        """
        Open and parse configuration from file

        @param   config_file  Configuration filename
        """
        super().__init__()

        config = ConfigParser()
        filename = canon.path(config_file)
        with open(filename, "r") as fp:
            config.read_file(fp)

        # Set main configurations
        for section in "precache", "irods", "httpd", "logging":
            self.add_config(section, _factories(section, config))

        # precache.index configuration depends upon precache.location
        precache_index = config.get("precache", "index")
        index_transform = partial(precache.index, self.precache.location)
        self.precache.add_value("index", ConfigValue(precache_index, index_transform))

        # Authentication handler configurations
        auth_config = Configuration()
        for handler in self.httpd.authentication:
            section = f"{handler}_auth"

            try:
                auth_config.add_config(handler, _factories(section, config))

            except KeyError:
                raise ParsingError(f"No configuration found for {handler} authentication")

        self.add_config("authentication", auth_config)

        # authentication.arvados.api_base_url depends upon .api_host and .api_version
        if "arvados" in self.authentication:
            api_host = self.authentication.arvados.api_host
            api_version = self.authentication.arvados.api_version

            if api_version == "v1":
                api_url = f"https://{api_host}/arvados/v1"
                self.authentication.arvados.add_value("api_base_url", ConfigValue(api_url, lambda x: x))
