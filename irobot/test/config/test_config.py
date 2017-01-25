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
from datetime import datetime
from tempfile import NamedTemporaryFile

from irobot.config import Configuration


class TestConfiguration(unittest.TestCase):
    def setUp(self):
        self.config_file = NamedTemporaryFile()

        self.config_file.writelines([
            "[precache]",
            "location = /foo",
            "index = bar",
            "size = unlimited",
            "expiry = unlimited",

            "[irods]",
            "max_connections = 30"
        ])
        self.config_file.flush()

    def tearDown(self):
        self.config_file.close()

    def test_config(self):
        config = Configuration(self.config_file.name)

        self.assertEqual(config.precache.location(), "/foo")
        self.assertEqual(config.precache.index(), "/foo/bar")
        self.assertIsNone(config.precache.size())
        self.assertIsNone(config.precache.expiry(datetime.utcnow()))


if __name__ == "__main__":
    unittest.main()
