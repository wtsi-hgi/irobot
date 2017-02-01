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
from ConfigParser import ParsingError

import irobot.config.misc as misc


class TestMiscConfig(unittest.TestCase):
    def test_log_level_parsing(self):
        parse_log_level = misc._parse_log_level

        self.assertRaises(ParsingError, parse_log_level, "foo")
        self.assertEqual(parse_log_level("debug"),    logging.DEBUG)
        self.assertEqual(parse_log_level("info"),     logging.INFO)
        self.assertEqual(parse_log_level("warning"),  logging.WARNING)
        self.assertEqual(parse_log_level("error"),    logging.ERROR)
        self.assertEqual(parse_log_level("critical"), logging.CRITICAL)

    def test_instance(self):
        config = misc.MiscConfig("debug")

        self.assertEqual(config.log_level(), logging.DEBUG)


if __name__ == "__main__":
    unittest.main()
