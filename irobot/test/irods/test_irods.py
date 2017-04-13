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
from unittest.mock import MagicMock, call, patch
from subprocess import CalledProcessError
from threading import Lock

from irobot.config.irods import iRODSConfig
from irobot.irods.irods import _exists, iRODS, iGetStatus


# Temporary data object for testing
TEST_DATAOBJECT_METADATA = {
    "collection": "/foo",
    "data_object": "bar",
    "checksum": "abcdef1234567890",
    "size": 1234,
    "avus": [
        {"attribute": "foo", "value": "bar"},
        {"attribute": "quux", "value": "xyzzy"}
    ],
    "access": [
        {"owner": "someone", "level": "own", "zone": "myZone"}
    ],
    "timestamps": [
        {"created": "1970-01-01T00:00:00", "replicates": 0},
        {"modified": "1970-01-01T00:00:00", "replicates": 0}
    ]
}


@patch("irobot.irods.irods.ils", spec=True)
class TestExists(unittest.TestCase):
    def test_exists_pass(self, mock_ils):
        _exists("/foo/bar")
        mock_ils.assert_called_once_with("/foo/bar")

    def test_exists_fail(self, mock_ils):
        mock_ils.side_effect = CalledProcessError(1, None, None)
        self.assertRaises(IOError, _exists, "/foo/bar")


class TestiRODS(unittest.TestCase):
    def setUp(self):
        config = iRODSConfig(max_connections="1")
        self.irods = iRODS(config)

    def tearDown(self):
        self.irods._iget_pool.shutdown()

    def test_worker_count(self):
        self.assertEqual(self.irods.workers, 1)

    @patch("concurrent.futures.ThreadPoolExecutor", spec=True)
    def test_destructor(self, mock_executor):
        self.irods._iget_pool = mock_executor()
        self.irods.__del__()
        self.irods._iget_pool.shutdown.assert_called_once()

    @patch("irobot.irods.irods._exists", spec=True)
    @patch("irobot.irods.irods.iget", spec=True)
    @patch("irobot.common.listenable._broadcast_time", spec=True)
    def test_get_dataobject(self, mock_broadcast_time, mock_iget, _mock_exists):
        lock = Lock()
        lock.acquire()

        def _check_messages(timestamp, status, irods_path):
            self.assertEqual(timestamp, mock_broadcast_time())
            self.assertEqual(irods_path, "/foo/bar")

            if status == iGetStatus.finished:
                lock.release()

        _listener = MagicMock()

        self.irods.add_listener(_listener)
        self.irods.add_listener(_check_messages)
        self.irods.get_dataobject("/foo/bar", "/quux/xyzzy")

        # Block until the _check_messages function unblocks
        lock.acquire()

        mock_iget.assert_called_once_with("/foo/bar", "/quux/xyzzy")

        # Make sure out listeners are getting the right messages
        _listener.assert_has_calls([
            call(mock_broadcast_time(), iGetStatus.queued, "/foo/bar"),
            call(mock_broadcast_time(), iGetStatus.started, "/foo/bar"),
            call(mock_broadcast_time(), iGetStatus.finished, "/foo/bar")
        ])

    @patch("irobot.irods.irods.iget", spec=True)
    @patch("irobot.common.listenable._broadcast_time", spec=True)
    def test_iget_pass(self, mock_broadcast_time, mock_iget):
        _listener = MagicMock()
        self.irods.add_listener(_listener)

        self.irods._iget("/foo/bar", "/quux/xyzzy")
        mock_iget.assert_called_once_with("/foo/bar", "/quux/xyzzy")
        _listener.assert_has_calls([
            call(mock_broadcast_time(), iGetStatus.started, "/foo/bar"),
            call(mock_broadcast_time(), iGetStatus.finished, "/foo/bar")
        ])

    @patch("irobot.irods.irods.iget", spec=True)
    @patch("irobot.common.listenable._broadcast_time", spec=True)
    def test_iget_fail(self, mock_broadcast_time, mock_iget):
        _listener = MagicMock()
        self.irods.add_listener(_listener)

        mock_iget.side_effect = CalledProcessError(1, "foo", "bar")

        self.irods._iget("/foo/bar", "/quux/xyzzy")
        mock_iget.assert_called_once_with("/foo/bar", "/quux/xyzzy")
        _listener.assert_has_calls([
            call(mock_broadcast_time(), iGetStatus.started, "/foo/bar"),
            call(mock_broadcast_time(), iGetStatus.failed, "/foo/bar")
        ])

    @patch("irobot.irods.irods.baton", spec=True)
    @patch("irobot.irods.irods.ils", spec=True)
    def test_get_metadata(self, mock_ils, mock_baton):
        mock_baton.return_value = TEST_DATAOBJECT_METADATA

        avu_metadata, fs_metadata = self.irods.get_metadata("/foo/bar")
        mock_ils.assert_called_once_with("/foo/bar")
        mock_baton.assert_called_once_with("/foo/bar")

        self.assertEqual(avu_metadata, TEST_DATAOBJECT_METADATA["avus"])

        for k in ["checksum", "size", "access", "timestamps"]:
            self.assertEqual(fs_metadata[k], TEST_DATAOBJECT_METADATA[k])


if __name__ == "__main__":
    unittest.main()
