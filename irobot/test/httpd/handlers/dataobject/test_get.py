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

from irobot.common import ByteRange
from irobot.httpd.handlers.dataobject._get import \
    _canonicalise_ranges as c, \
    _parse_range as pr


class TestRangeParser(unittest.TestCase):
    def test_FOO(self):
        # TODO
        pass


class TestRangeCanonicaliser(unittest.TestCase):
    def test_nothing(self):
        self.assertRaises(AssertionError, c)

    def test_single(self):
        self.assertEqual(c([ByteRange(1, 2)]),
                         [ByteRange(1, 2)])

    def test_multiple(self):
        self.assertEqual(c([ByteRange(1, 2), ByteRange(4, 5)], [ByteRange(7, 8)]),
                         [ByteRange(1, 2), ByteRange(4, 5), ByteRange(7, 8)])

    def test_ordered(self):
        self.assertEqual(c([ByteRange(7, 8), ByteRange(4, 5, "foo"), ByteRange(1, 2)]),
                         [ByteRange(1, 2), ByteRange(4, 5, "foo"), ByteRange(7, 8)])

    def test_juxtaposed(self):
        self.assertEqual(c([ByteRange(1, 2), ByteRange(3, 4)]),
                         [ByteRange(1, 4)])

        self.assertEqual(c([ByteRange(1, 2), ByteRange(3, 4, "foo")]),
                         [ByteRange(1, 2), ByteRange(3, 4, "foo")])

        self.assertEqual(c([ByteRange(1, 2, "foo"), ByteRange(3, 4)]),
                         [ByteRange(1, 2, "foo"), ByteRange(3, 4)])

        self.assertEqual(c([ByteRange(1, 2, "foo"), ByteRange(3, 4, "foo")]),
                         [ByteRange(1, 2, "foo"), ByteRange(3, 4, "foo")])

    def test_overlapping(self):
        self.assertEqual(c([ByteRange(1, 10), ByteRange(10, 20)]),
                         [ByteRange(1, 20)])

        self.assertEqual(c([ByteRange(1, 10), ByteRange(3, 8)]),
                         [ByteRange(1, 10)])

        self.assertEqual(c([ByteRange(10, 20), ByteRange(5, 15)]),
                         [ByteRange(5, 20)])

    def test_juxtaposed_checksum(self):
        self.assertEqual(c([ByteRange(1, 10), ByteRange(11, 20, "foo")]),
                         [ByteRange(1, 10), ByteRange(11, 20, "foo")])

        self.assertEqual(c([ByteRange(1, 10, "foo"), ByteRange(11, 20)]),
                         [ByteRange(1, 10, "foo"), ByteRange(11, 20)])

        self.assertEqual(c([ByteRange(1, 10, "foo"), ByteRange(11, 20, "bar")]),
                         [ByteRange(1, 10, "foo"), ByteRange(11, 20, "bar")])

    def test_interposed_checksum(self):
        self.assertEqual(c([ByteRange(1, 10), ByteRange(8, 15, "foo")]),
                         [ByteRange(1, 7), ByteRange(8, 15, "foo")])

        self.assertEqual(c([ByteRange(1, 10), ByteRange(3, 8, "foo")]),
                         [ByteRange(1, 2), ByteRange(3, 8, "foo"), ByteRange(9, 10)])


if __name__ == "__main__":
    unittest.main()
