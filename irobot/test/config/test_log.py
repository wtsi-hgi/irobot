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

import irobot.config.log as log


class TesLoggingConfig(unittest.TestCase):
    def test_output_parsing(self):
        canon_output = log._canon_output

        self.assertIsNone(canon_output("STDERR"))
        self.assertEqual(canon_output("/foo.log"), "/foo.log")

    def test_level_parsing(self):
        canon_level = log._canon_level

        self.assertRaises(ParsingError, canon_level, "foo")
        self.assertEqual(canon_level("debug"),    logging.DEBUG)
        self.assertEqual(canon_level("info"),     logging.INFO)
        self.assertEqual(canon_level("warning"),  logging.WARNING)
        self.assertEqual(canon_level("error"),    logging.ERROR)
        self.assertEqual(canon_level("critical"), logging.CRITICAL)

    def test_instance(self):
        config = log.LoggingConfig("/var/log/irobot.log", "debug")

        self.assertEqual(config.output(), "/var/log/irobot.log")
        self.assertEqual(config.level(), logging.DEBUG)
        self.assertRegex(str(config), r"output: /var/log/irobot.log")
        self.assertRegex(str(config), r"level: debug")


if __name__ == "__main__":
    unittest.main()
