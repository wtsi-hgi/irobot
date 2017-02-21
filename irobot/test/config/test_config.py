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

import logging
import unittest
from configparser import ParsingError
from datetime import datetime, timedelta
from tempfile import NamedTemporaryFile

from irobot.config import Configuration
from irobot.config._base import BaseConfig
from irobot.config.config import _AuthHandlers


PRECACHE_CONF = [
    "[precache]",
    "location = /foo",
    "index = bar",
    "size = unlimited",
    "expiry = unlimited",
    "chunk_size = 64MB"
]

IRODS_CONF = [
    "[irods]",
    "max_connections = 30"
]

HTTPD_CONF = [
    "[httpd]",
    "bind_address = 0.0.0.0",
    "listen = 5000",
    "timeout = 500",
    "authentication = basic, arvados"
]

BASIC_AUTH_CONF = [
    "[basic_auth]",
    "url = http://example.com",
    "cache = never"
]

ARVADOS_AUTH_CONF = [
    "[arvados_auth]",
    "api_host = api.arvados.example.com",
    "api_version = v1",
    "cache = never"
]

LOGGING_CONF = [
    "[logging]",
    "output = STDERR",
    "level = warning"
]


class _FooConfig(BaseConfig):
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def get(self, k):
        return self.kwargs[k]


class TestAuthHandlers(unittest.TestCase):
    def test_container(self):
        configs = {"a": BaseConfig(), "b": BaseConfig(), "c": BaseConfig()}
        container = _AuthHandlers(**configs)

        for k, v in configs.items():
            self.assertEqual(getattr(container, k), v)


class TestConfiguration(unittest.TestCase):
    def setUp(self):
        self.config_file = NamedTemporaryFile(mode="w+t", delete=True)

        self.config_file.write("\n".join(
            PRECACHE_CONF +
            IRODS_CONF +
            HTTPD_CONF +
            BASIC_AUTH_CONF +
            ARVADOS_AUTH_CONF +
            LOGGING_CONF +
            ["[foo]", "bar = 123", "quux = 456", "xyzzy = 789"]
        ))
        self.config_file.flush()

    def tearDown(self):
        self.config_file.close()

    def test_invalid_file(self):
        self.assertRaises(IOError, Configuration, "/this_file_probably_does_not_exist")

    def test_builder(self):
        config = Configuration(self.config_file.name)
        foo = config._build_config(_FooConfig, "foo", "bar", "quux", "xyzzy")

        self.assertEqual(foo.get("bar"),   "123")
        self.assertEqual(foo.get("quux"),  "456")
        self.assertEqual(foo.get("xyzzy"), "789")

    def test_get_config(self):
        config = Configuration(self.config_file.name)

        sections = list(config.get_sections().keys())
        expected = ["precache", "irods", "httpd", "logging"]
        self.assertEqual(sorted(sections), sorted(expected))

    def test_config(self):
        config = Configuration(self.config_file.name)

        self.assertEqual(config.file, self.config_file.name)

        self.assertEqual(config.precache.location, "/foo")
        self.assertEqual(config.precache.index, "/foo/bar")
        self.assertIsNone(config.precache.size)
        self.assertIsNone(config.precache.expiry(datetime.utcnow()))
        self.assertEqual(config.precache.chunk_size, 64 * (1000**2))

        self.assertEqual(config.irods.max_connections, 30)

        self.assertEqual(config.httpd.bind_address, "0.0.0.0")
        self.assertEqual(config.httpd.listen, 5000)
        self.assertEqual(config.httpd.timeout, timedelta(milliseconds=500))
        self.assertEqual(config.httpd.authentication, ["basic", "arvados"])

        self.assertEqual(config.authentication.basic.url, "http://example.com")
        self.assertIsNone(config.authentication.basic.cache)

        self.assertEqual(config.authentication.arvados.api_host, "api.arvados.example.com")
        self.assertEqual(config.authentication.arvados.api_version, "v1")
        self.assertEqual(config.authentication.arvados.api_base_url, "https://api.arvados.example.com/arvados/v1")
        self.assertIsNone(config.authentication.arvados.cache)

        self.assertIsNone(config.logging.output)
        self.assertEqual(config.logging.level, logging.WARNING)

    def test_unknown_http_auth_method(self):
        with NamedTemporaryFile(mode="w+t") as config_file:
            bad_httpd_conf = [op for op in HTTPD_CONF if not op.startswith("authentication")] \
                           + ["authentication = foo"]

            config_file.write("\n".join(PRECACHE_CONF + IRODS_CONF + LOGGING_CONF + bad_httpd_conf))
            config_file.flush()

            self.assertRaises(ParsingError, Configuration, config_file.name)


if __name__ == "__main__":
    unittest.main()
