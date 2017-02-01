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

import unittest
import logging
from datetime import datetime
from tempfile import NamedTemporaryFile

from irobot.config import Configuration


class _FooConfig(object):
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def get(self, k):
        return self.kwargs[k]


class TestConfiguration(unittest.TestCase):
    def setUp(self):
        self.config_file = NamedTemporaryFile(delete=True)

        self.config_file.write("\n".join([
            "[precache]",
            "location = /foo",
            "index = bar",
            "size = unlimited",
            "expiry = unlimited",
            "chunk_size = 64MB",

            "[irods]",
            "max_connections = 30",

            "[httpd]",
            "bind_address = 0.0.0.0",
            "listen = 5000",

            "[misc]",
            "log_level = warning",

            "[foo]",
            "bar = 123",
            "quux = 456",
            "xyzzy = 789"
        ]))
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

    def test_config(self):
        config = Configuration(self.config_file.name)

        self.assertEqual(config.precache.location(), "/foo")
        self.assertEqual(config.precache.index(), "/foo/bar")
        self.assertIsNone(config.precache.size())
        self.assertIsNone(config.precache.expiry(datetime.utcnow()))
        self.assertEqual(config.precache.chunk_size(), 64 * (1000**2))

        self.assertEqual(config.irods.max_connections(), 30)

        self.assertEqual(config.httpd.bind_address(), "0.0.0.0")
        self.assertEqual(config.httpd.listen(), 5000)

        self.assertEqual(config.misc.log_level(), logging.WARNING)


if __name__ == "__main__":
    unittest.main()
