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

import filecmp
import os
import unittest
from hashlib import md5
from multiprocessing import cpu_count
from tempfile import NamedTemporaryFile, TemporaryDirectory
from threading import Lock
from unittest.mock import MagicMock, call, patch

from irobot.common import AsyncTaskStatus, ByteRange
from irobot.config import PrecacheConfig
from irobot.config._tree_builder import ConfigValue
from irobot.precache._checksummer import Checksummer, _checksum, _parse_checksum_record

_mock_checksum = "0123456789abcdef0123456789abcdef"


class TestInternals(unittest.TestCase):
    def test_parse_checksum_record(self):
        passing_tests = [
            (f"*\t{_mock_checksum}", ByteRange(0, -1, _mock_checksum)),
            (f"0-10\t{_mock_checksum}", ByteRange(0, 10, _mock_checksum)),
            (f"123-456\t{_mock_checksum}", ByteRange(123, 456, _mock_checksum)),
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

    def test_checksummer(self):
        data = b"\0" * 15

        whole_checksum = md5(data).hexdigest()
        chunk_checksum = md5(b"\0" * 10).hexdigest()
        remainder_checksum = md5(b"\0" * 5).hexdigest()

        tmp = NamedTemporaryFile(mode="w+b", delete=False)
        tmp.write(data)
        tmp.close()

        filename, checksums = _checksum(tmp.name, 10)
        self.assertEqual(filename, tmp.name)
        self.assertEqual(checksums, [ByteRange(0, -1, whole_checksum),
                                     ByteRange(0, 10, chunk_checksum),
                                     ByteRange(10, 15, remainder_checksum)])

        _, checksums = _checksum(tmp.name, 10, ByteRange(5, 15))
        self.assertEqual(checksums, [ByteRange(5, 10, remainder_checksum),
                                     ByteRange(10, 15, remainder_checksum)])

        _, checksums = _checksum(tmp.name, 5, ByteRange(0, 15))
        self.assertEqual(checksums, [ByteRange(0, 5, remainder_checksum),
                                     ByteRange(5, 10, remainder_checksum),
                                     ByteRange(10, 15, remainder_checksum)])

        os.remove(tmp.name)


class TestChecksummer(unittest.TestCase):
    def setUp(self):
        self.chunk_size = chunk_size = 10  # bytes

        config = PrecacheConfig()
        config.add_value("location", ConfigValue("/foo", str))
        config.add_value("index", ConfigValue("/foo/bar", str))
        config.add_value("size", ConfigValue(None, lambda x: x))
        config.add_value("expiry", ConfigValue(None, lambda x: x))
        config.add_value("chunk_size", ConfigValue(chunk_size, int))
        self.checksummer = Checksummer(config)

        self.temp_precache = TemporaryDirectory()

        # Create mock data file (zero filled)
        with open(os.path.join(self.temp_precache.name, "data"), "wb") as data_fd:
            self.data_size = data_size = 25
            data = b"\0" * data_size
            data_fd.write(data)

        # Create mock checksum file
        with open(os.path.join(self.temp_precache.name, "manual_checksums"), "wt") as checksums_fd:
            whole_checksum = md5(data).hexdigest()
            chunk_checksum = md5(b"\0" * chunk_size).hexdigest()

            checksums_fd.write(f"*\t{whole_checksum}\n")

            for x in range(data_size // chunk_size):
                last_index = (x + 1) * chunk_size
                checksums_fd.write(f"{x * chunk_size}-{last_index}\t{chunk_checksum}\n")

            remainder = data_size % chunk_size
            if remainder:
                remainder_checksum = md5(b"\0" * remainder).hexdigest()
                checksums_fd.write(f"{last_index}-{data_size}\t{remainder_checksum}\n")

    def tearDown(self):
        self.temp_precache.cleanup()
        self.checksummer.pool.shutdown()

    def test_worker_count(self):
        self.assertEqual(self.checksummer.workers, cpu_count() * 5)

    @patch("concurrent.futures.ThreadPoolExecutor", spec=True)
    def test_cleanup(self, mock_executor):
        self.checksummer.pool = mock_executor()
        self.checksummer.__del__()
        self.checksummer.pool.shutdown.assert_called_once()

    @patch("irobot.common.listenable._broadcast_time", spec=True)
    def test_generate_checksum_file(self, mock_broadcast_time):
        # NOTE This test actually checks that the checksumming works
        # correctly, even though we test the checksummer individually
        # elsewhere. This makes the test complicated (to synchronise
        # everything), when really all we need to check is that the call
        # graph is correct...
        lock = Lock()
        lock.acquire()

        def _check_results(timestamp, status, precache_path):
            if status == AsyncTaskStatus.finished:
                generated = os.path.join(self.temp_precache.name, "checksums")
                manual = os.path.join(self.temp_precache.name, "manual_checksums")

                try:
                    self.assertTrue(filecmp.cmp(generated, manual, shallow=False))
                finally:
                    lock.release()

        mock_listener = MagicMock()

        self.checksummer.add_listener(_check_results)
        self.checksummer.add_listener(mock_listener)
        self.checksummer.generate_checksum_file(self.temp_precache.name)

        # Block until the _check_results function unlocks
        lock.acquire()

        # Make sure our listeners are getting the right messages
        mock_listener.assert_has_calls([
            call(mock_broadcast_time(), AsyncTaskStatus.started, self.temp_precache.name),
            call(mock_broadcast_time(), AsyncTaskStatus.finished, self.temp_precache.name)
        ])

    def test_get_checksummed_blocks(self):
        self.assertRaises(FileNotFoundError, self.checksummer.get_checksummed_blocks, "foo")

        # Use our manually created checksum file, instead of generating
        os.rename(os.path.join(self.temp_precache.name, "manual_checksums"),
                  os.path.join(self.temp_precache.name, "checksums"))

        self.assertRaises(IndexError, self.checksummer.get_checksummed_blocks, self.temp_precache.name,
                          ByteRange(0, self.data_size + 10))

        whole_checksum = md5(b"\0" * self.data_size).hexdigest()
        chunk_checksum = md5(b"\0" * self.chunk_size).hexdigest()
        remainder_checksum = md5(b"\0" * (self.data_size % self.chunk_size)).hexdigest()

        # Get whole checksum
        checksums = self.checksummer.get_checksummed_blocks(self.temp_precache.name)
        self.assertEqual(len(checksums), 1)
        self.assertEqual(checksums[0].checksum, whole_checksum)

        # Get checksums for range (whole file)
        checksums = self.checksummer.get_checksummed_blocks(self.temp_precache.name, ByteRange(0, self.data_size))
        self.assertEqual(checksums[-1].checksum, remainder_checksum)
        for i, _chunk in enumerate(checksums[:-1]):
            index = i * self.chunk_size, (i + 1) * self.chunk_size
            self.assertEqual(checksums[i], ByteRange(*index, chunk_checksum))

        # Get checksum for partial chunk
        partial_chunk = ByteRange(1, self.chunk_size - 1)
        partial_chunk_size = partial_chunk.finish - partial_chunk.start
        checksums = self.checksummer.get_checksummed_blocks(self.temp_precache.name, partial_chunk)
        self.assertEqual(len(checksums), 1)
        self.assertEqual(checksums[0], ByteRange(partial_chunk.start, partial_chunk.finish,
                                                 md5(b"\0" * partial_chunk_size).hexdigest()))

    def test_calculate_checksum_filesize(self):
        checksum_file_size = os.stat(os.path.join(self.temp_precache.name, "manual_checksums")).st_size
        self.assertEqual(self.checksummer.calculate_checksum_filesize(self.data_size), checksum_file_size)


if __name__ == "__main__":
    unittest.main()
