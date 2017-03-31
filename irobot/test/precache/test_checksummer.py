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

from irobot.precache._checksummer import _parse_checksum_record


class TestInternals(unittest.TestCase):
    def test_parse_checksum_record(self):
        test_checksum = "0123456789abcdef0123456789abcdef"
        passing_tests = [
            (f"*\t{test_checksum}", (None, test_checksum)),
            (f"0-10\t{test_checksum}", ((0, 10), test_checksum)),
            (f"123-456\t{test_checksum}", ((123, 456), test_checksum)),
        ]

        for record, expected in passing_tests:
            self.assertEqual(_parse_checksum_record(record), expected)

    def test_parse_bad_checksum_record(self):
        failing_tests = [
            "",
            "*",
            "* 0123456789abcdef0123456789abcdef",
            "*\tabc123",
            "*\t",
            "\t0123456789abcdef0123456789abcdef",
            "123-abc\t0123456789abcdef0123456789abcdef",
            "123-456 0123456789abcdef0123456789abcdef"
        ]

        for record in failing_tests:
            self.assertRaises(SyntaxError, _parse_checksum_record, record)


if __name__ == "__main__":
    unittest.main()
