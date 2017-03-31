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

from irobot.config.precache import PrecacheConfig
from irobot.precache._checksummer import Checksummer, _parse_checksum_record


_mock_checksum = "0123456789abcdef0123456789abcdef"


class TestInternals(unittest.TestCase):
    def test_parse_checksum_record(self):
        passing_tests = [
            (f"*\t{_mock_checksum}", (None, _mock_checksum)),
            (f"0-10\t{_mock_checksum}", ((0, 10), _mock_checksum)),
            (f"123-456\t{_mock_checksum}", ((123, 456), _mock_checksum)),
        ]

        for record, expected in passing_tests:
            self.assertEqual(_parse_checksum_record(record), expected)

    def test_parse_bad_checksum_record(self):
        failing_tests = [
            "",
            "*",
            f"* {_mock_checksum}",
            "*\tabc123",
            "*\t",
            f"\t{_mock_checksum}",
            f"123-abc\t{_mock_checksum}",
            f"123-456 {_mock_checksum}"
        ]

        for record in failing_tests:
            self.assertRaises(SyntaxError, _parse_checksum_record, record)


class TestChecksummer(unittest.TestCase):
    def setUp(self):
        config = PrecacheConfig("/foo", "bar", "unlimited", "unlimited", "10B")
        self.checksummer = Checksummer(config)

    def test_calculate_checksum_filesize(self):
        data_size = 25
        mock_checksum_file = "\n".join([
            f"*\t{_mock_checksum}",
            f"0-10\t{_mock_checksum}",
            f"10-20\t{_mock_checksum}",
            f"20-25\t{_mock_checksum}",
            "",
        ])

        self.assertEqual(self.checksummer.calculate_checksum_filesize(data_size), len(mock_checksum_file))


if __name__ == "__main__":
    unittest.main()
