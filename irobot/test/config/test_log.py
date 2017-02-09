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
from ConfigParser import ParsingError

import irobot.config.log as log


class TesLoggingConfig(unittest.TestCase):
    def test_output_parsing(self):
        parse_output = log._parse_output

        self.assertIsNone(parse_output("STDERR"))
        self.assertEqual(parse_output("/foo.log"), "/foo.log")

    def test_level_parsing(self):
        parse_level = log._parse_level

        self.assertRaises(ParsingError, parse_level, "foo")
        self.assertEqual(parse_level("debug"),    logging.DEBUG)
        self.assertEqual(parse_level("info"),     logging.INFO)
        self.assertEqual(parse_level("warning"),  logging.WARNING)
        self.assertEqual(parse_level("error"),    logging.ERROR)
        self.assertEqual(parse_level("critical"), logging.CRITICAL)

    def test_instance(self):
        config = log.LoggingConfig("/var/log/irobot.log", "debug")

        self.assertEqual(config.output(), "/var/log/irobot.log")
        self.assertEqual(config.level(), logging.DEBUG)
        self.assertRegexpMatches(str(config), r"output: /var/log/irobot.log")
        self.assertRegexpMatches(str(config), r"level: debug")


if __name__ == "__main__":
    unittest.main()