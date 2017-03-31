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
from hashlib import md5
from tempfile import TemporaryDirectory

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
        chunk_size = 10 # bytes

        config = PrecacheConfig("/foo", "bar", "unlimited", "unlimited", f"{chunk_size}B")
        self.checksummer = Checksummer(config)

        self.temp_precache = TemporaryDirectory()

        # Create mock data file (zero filled)
        with open(os.path.join(self.temp_precache.name, "data"), "wb") as data_fd:
            self.data_size = 25
            data = b"\0" * self.data_size
            data_fd.write(data)

        # Create mock checksum file
        with open(os.path.join(self.temp_precache.name, "checksums"), "wt") as checksums_fd:
            whole_checksum = md5(data).hexdigest()
            chunk_checksum = md5(b"\0" * chunk_size).hexdigest()

            checksums_fd.write(f"*\t{whole_checksum}\n")

            for x in range(self.data_size // chunk_size):
                last_index = (x + 1) * chunk_size
                checksums_fd.write(f"{x * chunk_size}-{last_index}\t{chunk_checksum}\n")

            remainder = self.data_size % chunk_size
            if remainder:
                remainder_checksum = md5(b"\0" * remainder).hexdigest()
                checksums_fd.write(f"{last_index}-{self.data_size}\t{remainder_checksum}\n")

    def tearDown(self):
        self.temp_precache.cleanup()
    
    def test_get_checksummed_blocks(self):
        self.assertRaises(FileNotFoundError, self.checksummer.get_checksummed_blocks, "foo")

        # TODO

    def test_calculate_checksum_filesize(self):
        checksum_file_size = os.stat(os.path.join(self.temp_precache.name, "checksums")).st_size
        self.assertEqual(self.checksummer.calculate_checksum_filesize(self.data_size), checksum_file_size)


if __name__ == "__main__":
    unittest.main()
