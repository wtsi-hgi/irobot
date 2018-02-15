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

import irobot.config._precache as precache
from irobot.common import add_years


class TestPrecacheConfig(unittest.TestCase):
    def setUp(self):
        self.now = datetime.utcnow()
        self.cwd = os.getcwd()
        self.homedir = os.path.expanduser("~")

    def test_index_parsing(self):
        canon_index = precache.index

        self.assertRaises(ParsingError, canon_index, "", "foo/")
        self.assertEqual(canon_index("", "foo"), "foo")
        self.assertEqual(canon_index("foo", "bar"), "foo/bar")
        self.assertEqual(canon_index("", "/foo/bar"), "/foo/bar")

    def test_size_parsing(self):
        canon_limited_size = precache.limited_size
        canon_unlimited_size = precache.unlimited_size

        self.assertRaises(ParsingError, canon_limited_size, "foo")
        self.assertRaises(ParsingError, canon_limited_size, "unlimited")
        self.assertRaises(ParsingError, canon_limited_size, "1.23 B")
        self.assertRaises(ParsingError, canon_unlimited_size, "foo")

        self.assertIsNone(canon_unlimited_size("unlimited"))
        self.assertEqual(canon_limited_size("123"), 123)

    def test_parse_expiry(self):
        parse_expiry = precache._parse_expiry

        self.assertRaises(ParsingError, parse_expiry, "foo")
        self.assertIsNone(parse_expiry("unlimited"))
        self.assertEqual(parse_expiry("1h"), (1, "h"))
        self.assertEqual(parse_expiry("1 hour"), (1, "h"))
        self.assertEqual(parse_expiry("1.2 hours"), (1.2, "h"))
        self.assertEqual(parse_expiry("1d"), (1, "d"))
        self.assertEqual(parse_expiry("1 day"), (1, "d"))
        self.assertEqual(parse_expiry("1.2 days"), (1.2, "d"))
        self.assertEqual(parse_expiry("1w"), (1, "w"))
        self.assertEqual(parse_expiry("1 week"), (1, "w"))
        self.assertEqual(parse_expiry("1.2 weeks"), (1.2, "w"))
        self.assertEqual(parse_expiry("1y"), (1, "y"))
        self.assertEqual(parse_expiry("1 year"), (1, "y"))
        self.assertEqual(parse_expiry("1.2 years"), (1.2, "y"))

    def test_expiry_parsing(self):
        now = datetime.utcnow()
        dt = lambda exp: precache.expiry(exp)(now) - now

        self.assertIsNone(precache.expiry("unlimited")(now))
        self.assertEqual(dt("1h"), timedelta(hours=1))
        self.assertEqual(dt("1 hour"), timedelta(hours=1))
        self.assertEqual(dt("1.2 hours"), timedelta(hours=1.2))
        self.assertEqual(dt("1d"), timedelta(days=1))
        self.assertEqual(dt("1 day"), timedelta(days=1))
        self.assertEqual(dt("1.2 days"), timedelta(days=1.2))
        self.assertEqual(dt("1w"), timedelta(weeks=1))
        self.assertEqual(dt("1 week"), timedelta(weeks=1))
        self.assertEqual(dt("1.2 weeks"), timedelta(weeks=1.2))
        self.assertEqual(dt("1y"), add_years(now, 1) - now)
        self.assertEqual(dt("1 year"), add_years(now, 1) - now)
        self.assertEqual(dt("1.2 years"), add_years(now, 1.2) - now)

    def test_age_threshold_parsing(self):
        canon_age_threshold = precache.age_threshold

        self.assertIsNone(canon_age_threshold(None))
        self.assertEqual(canon_age_threshold("1 hour"), timedelta(hours=1))
        self.assertEqual(canon_age_threshold("1 day"), timedelta(days=1))
        self.assertEqual(canon_age_threshold("1 week"), timedelta(days=7))
        self.assertEqual(canon_age_threshold("1 year"), timedelta(days=365))


if __name__ == "__main__":
    unittest.main()
