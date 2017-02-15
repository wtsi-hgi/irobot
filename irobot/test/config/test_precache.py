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

import os
import unittest
from configparser import ParsingError
from datetime import datetime, timedelta

import irobot.config.precache as precache
from irobot.common import add_years


class TestPrecacheConfig(unittest.TestCase):
    def setUp(self):
        self.now = datetime.utcnow()
        self.cwd = os.getcwd()
        self.homedir = os.path.expanduser("~")

    def test_location_parsing(self):
        parse_location = precache._parse_location

        self.assertEqual(parse_location("/foo"), "/foo")
        self.assertEqual(parse_location("~/foo"), os.path.join(self.homedir, "foo"))
        self.assertEqual(parse_location("foo"), os.path.join(self.cwd, "foo"))

    def test_index_parsing(self):
        parse_index = precache._parse_index

        self.assertRaises(ParsingError, parse_index, "", "foo/")
        self.assertEqual(parse_index("", "foo"), "foo")
        self.assertEqual(parse_index("foo", "bar"), "foo/bar")
        self.assertEqual(parse_index("", "/foo/bar"), "/foo/bar")

    def test_size_parsing(self):
        parse_limited_size = precache._parse_limited_size
        parse_unlimited_size = precache._parse_unlimited_size

        self.assertRaises(ParsingError, parse_limited_size, "foo")
        self.assertRaises(ParsingError, parse_limited_size, "unlimited")
        self.assertRaises(ParsingError, parse_limited_size, "1.23 B")
        self.assertRaises(ParsingError, parse_unlimited_size, "foo")

        self.assertIsNone(parse_unlimited_size("unlimited"))
        self.assertEqual(parse_limited_size("123"), 123)

    def test_expiry_parsing(self):
        parse_expiry = precache._parse_expiry

        self.assertRaises(ParsingError, parse_expiry, "foo")
        self.assertIsNone(parse_expiry("unlimited"))
        self.assertEqual(parse_expiry("1h"), timedelta(hours = 1))
        self.assertEqual(parse_expiry("1 hour"), timedelta(hours = 1))
        self.assertEqual(parse_expiry("1.2 hours"), timedelta(hours = 1.2))
        self.assertEqual(parse_expiry("1d"), timedelta(days = 1))
        self.assertEqual(parse_expiry("1 day"), timedelta(days = 1))
        self.assertEqual(parse_expiry("1.2 days"), timedelta(days = 1.2))
        self.assertEqual(parse_expiry("1w"), timedelta(weeks = 1))
        self.assertEqual(parse_expiry("1 week"), timedelta(weeks = 1))
        self.assertEqual(parse_expiry("1.2 weeks"), timedelta(weeks = 1.2))
        self.assertEqual(parse_expiry("1y"), 1)
        self.assertEqual(parse_expiry("1 year"), 1)
        self.assertEqual(parse_expiry("1.2 years"), 1.2)

    def test_instance(self):
        config = precache.PrecacheConfig("/foo", "bar", "123 GB", "unlimited", "64MB")
        self.assertEqual(config.location(), "/foo")
        self.assertEqual(config.index(), "/foo/bar")
        self.assertEqual(config.size(), 123 * (1000**3))
        self.assertIsNone(config.expiry(self.now))
        self.assertEqual(config.chunk_size(), 64 * (1000**2))
        self.assertRegex(str(config), r"expiry: unlimited")

        config = precache.PrecacheConfig("/foo", "bar", "123 GB", "3 weeks", "64MB")
        self.assertEqual(config.expiry(self.now), self.now + timedelta(weeks = 3))
        self.assertRegex(str(config), r"expiry: 21 days")

        config = precache.PrecacheConfig("/foo", "bar", "123 GB", "1.2 years", "64MB")
        self.assertEqual(config.expiry(self.now), add_years(self.now, 1.2))
        self.assertRegex(str(config), r"expiry: 1.2 years")


if __name__ == "__main__":
    unittest.main()
