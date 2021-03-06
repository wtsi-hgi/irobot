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

from aiohttp.web import HTTPRequestRangeNotSatisfiable as exc416

from irobot.common import ByteRange
from irobot.httpd.handlers.dataobject._range_parser import \
    canonicalise_ranges as c, \
    parse_range as pr


class TestRangeParser(unittest.TestCase):
    def test_invalid_input(self):
        self.assertRaises(exc416, pr, "foo", 123)

    def test_invalid_unit(self):
        self.assertRaises(exc416, pr, "foo=123-456", 500)

    def test_invalid_range(self):
        self.assertRaises(exc416, pr, "bytes=-", 500)
        self.assertRaises(exc416, pr, "bytes=456-123", 500)

    def test_range_out_of_bounds(self):
        self.assertRaises(exc416, pr, "bytes=500-1000", 400)

    def test_full_range(self):
        self.assertEqual(pr("bytes=100-200", 500),
                         [ByteRange(100, 201)])

    def test_right_truncation(self):
        self.assertEqual(pr("bytes=100-300", 200),
                         [ByteRange(100, 200)])

    def test_from_range(self):
        self.assertEqual(pr("bytes=100-", 500),
                         [ByteRange(100, 500)])

    def test_from_end_range(self):
        self.assertEqual(pr("bytes=-100", 500),
                         [ByteRange(400, 500)])

    def test_multiple_range(self):
        self.assertEqual(pr("bytes=10-20,30-40,50-60", 100),
                         [ByteRange(10, 21), ByteRange(30, 41), ByteRange(50, 61)])

    def test_range_canonicalisation(self):
        self.assertEqual(pr("bytes=10-20,21-30", 500),
                         [ByteRange(10, 31)])

        self.assertEqual(pr("bytes=10-20,18-30", 500),
                         [ByteRange(10, 31)])

        self.assertEqual(pr("bytes=10-20,12-18", 500),
                         [ByteRange(10, 21)])


class TestRangeCanonicaliser(unittest.TestCase):
    def test_nothing(self):
        self.assertRaises(AssertionError, c)
        self.assertRaises(AssertionError, c, [])

    def test_single(self):
        self.assertEqual(c([ByteRange(1, 2)]),
                         [ByteRange(1, 2)])

    def test_ordering(self):
        self.assertEqual(c([ByteRange(7, 8), ByteRange(4, 5, "foo"), ByteRange(1, 2)]),
                         [ByteRange(1, 2), ByteRange(4, 5, "foo"), ByteRange(7, 8)])

    def test_separate(self):
        self.assertEqual(c([ByteRange(1, 2), ByteRange(4, 5)], [ByteRange(7, 8)]),
                         [ByteRange(1, 2), ByteRange(4, 5), ByteRange(7, 8)])

        self.assertEqual(c([ByteRange(1, 2), ByteRange(4, 5, "foo")]),
                         [ByteRange(1, 2), ByteRange(4, 5, "foo")])

        self.assertEqual(c([ByteRange(1, 2, "foo"), ByteRange(4, 5)]),
                         [ByteRange(1, 2, "foo"), ByteRange(4, 5)])

        self.assertEqual(c([ByteRange(1, 2, "foo"), ByteRange(4, 5, "bar")]),
                         [ByteRange(1, 2, "foo"), ByteRange(4, 5, "bar")])

    def test_juxtaposed(self):
        self.assertEqual(c([ByteRange(1, 2), ByteRange(2, 3)]),
                         [ByteRange(1, 3)])

        self.assertEqual(c([ByteRange(1, 2), ByteRange(2, 3, "foo")]),
                         [ByteRange(1, 2), ByteRange(2, 3, "foo")])

        self.assertEqual(c([ByteRange(1, 2, "foo"), ByteRange(2, 3)]),
                         [ByteRange(1, 2, "foo"), ByteRange(2, 3)])

        self.assertEqual(c([ByteRange(1, 2, "foo"), ByteRange(2, 3, "foo")]),
                         [ByteRange(1, 2, "foo"), ByteRange(2, 3, "foo")])

    def test_overlapping(self):
        self.assertEqual(c([ByteRange(1, 12), ByteRange(8, 20)]),
                         [ByteRange(1, 20)])

        self.assertEqual(c([ByteRange(1, 12), ByteRange(8, 20, "foo")]),
                         [ByteRange(1, 8), ByteRange(8, 20, "foo")])

        self.assertEqual(c([ByteRange(1, 12, "foo"), ByteRange(8, 20)]),
                         [ByteRange(1, 12, "foo"), ByteRange(12, 20)])

    def test_interposed(self):
        self.assertEqual(c([ByteRange(1, 20), ByteRange(5, 15)]),
                         [ByteRange(1, 20)])

        self.assertEqual(c([ByteRange(1, 20), ByteRange(5, 15, "foo")]),
                         [ByteRange(1, 5), ByteRange(5, 15, "foo"), ByteRange(15, 20)])

        self.assertEqual(c([ByteRange(1, 20, "foo"), ByteRange(5, 15)]),
                         [ByteRange(1, 20, "foo")])


if __name__ == "__main__":
    unittest.main()
