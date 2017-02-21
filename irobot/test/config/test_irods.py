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
from configparser import ParsingError

import irobot.config.irods as irods


class TestiRODSConfig(unittest.TestCase):
    def test_max_connection_parsing(self):
        canon_max_connections = irods._canon_max_connections

        self.assertEqual(canon_max_connections("10"), 10)
        self.assertRaises(ParsingError, canon_max_connections, "0")
        self.assertRaises(ParsingError, canon_max_connections, "-5")

    def test_instance(self):
        config = irods.iRODSConfig("123")

        self.assertEqual(config.max_connections, 123)


if __name__ == "__main__":
    unittest.main()
