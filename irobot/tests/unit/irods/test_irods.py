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

import json
import unittest
from subprocess import CalledProcessError
from threading import Lock
from unittest.mock import MagicMock, call, patch

from irobot.common import AsyncTaskStatus
from irobot.config import iRODSConfig
from irobot.config._tree_builder import ConfigValue
from irobot.irods._types import MetadataJSONDecoder
from irobot.irods.irods import Irods, IrodsError
from irobot.tests.unit.irods._common import TEST_BATON_JSON


@patch("irobot.irods.irods.ils", spec=True)
class TestExists(unittest.TestCase):
    def test_exists_pass(self, mock_ils):
        Irods.check_access("/foo/bar")
        mock_ils.assert_called_once_with("/foo/bar")

    def test_exists_fail(self, mock_ils):
        mock_ils.side_effect = IrodsError(1, "ERROR: -317000 USER_INPUT_PATH_ERR")
        self.assertRaises(FileNotFoundError, Irods.check_access, "/foo/bar")

        mock_ils.side_effect = IrodsError(1, "ERROR: -818000 CAT_NO_ACCESS_PERMISSION")
        self.assertRaises(PermissionError, Irods.check_access, "/foo/bar")

        mock_ils.side_effect = IrodsError(1, "Something has gone horribly wrong!")
        self.assertRaises(IOError, Irods.check_access, "/foo/bar")


class TestIrods(unittest.TestCase):
    def setUp(self):
        config = iRODSConfig()
        config.add_value("max_connections", ConfigValue(1, lambda x: x))
        self.irods = Irods(config)

    def tearDown(self):
        self.irods._iget_pool.shutdown()

    def test_worker_count(self):
        self.assertEqual(self.irods.workers, 1)

    @patch("concurrent.futures.ThreadPoolExecutor", spec=True)
    def test_destructor(self, mock_executor):
        self.irods._iget_pool = mock_executor()
        self.irods.__del__()
        self.irods._iget_pool.shutdown.assert_called_once()

    @patch("irobot.irods.irods.ils", spec=True)
    @patch("irobot.irods.irods.iget", spec=True)
    @patch("irobot.common.listenable._broadcast_time", spec=True)
    def test_get_dataobject(self, mock_broadcast_time, mock_iget, _mock_ils):
        lock = Lock()
        lock.acquire()

        def _check_messages(timestamp, status, irods_path, local_path):
            self.assertEqual(timestamp, mock_broadcast_time())
            self.assertEqual(irods_path, "/foo/bar")
            self.assertEqual(local_path, "/quux/xyzzy")

            if status == AsyncTaskStatus.finished:
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
            call(mock_broadcast_time(), AsyncTaskStatus.queued, "/foo/bar", "/quux/xyzzy"),
            call(mock_broadcast_time(), AsyncTaskStatus.started, "/foo/bar", "/quux/xyzzy"),
            call(mock_broadcast_time(), AsyncTaskStatus.finished, "/foo/bar", "/quux/xyzzy")
        ])

    @patch("irobot.irods.irods.iget", spec=True)
    @patch("irobot.common.listenable._broadcast_time", spec=True)
    def test_iget_pass(self, mock_broadcast_time, mock_iget):
        _listener = MagicMock()
        self.irods.add_listener(_listener)

        self.irods._iget("/foo/bar", "/quux/xyzzy")
        mock_iget.assert_called_once_with("/foo/bar", "/quux/xyzzy")
        _listener.assert_has_calls([
            call(mock_broadcast_time(), AsyncTaskStatus.started, "/foo/bar", "/quux/xyzzy"),
            call(mock_broadcast_time(), AsyncTaskStatus.finished, "/foo/bar", "/quux/xyzzy")
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
            call(mock_broadcast_time(), AsyncTaskStatus.started, "/foo/bar", "/quux/xyzzy"),
            call(mock_broadcast_time(), AsyncTaskStatus.failed, "/foo/bar", "/quux/xyzzy")
        ])

    @patch("irobot.irods.irods.baton", spec=True)
    @patch("irobot.irods.irods.ils", spec=True)
    def test_get_metadata(self, mock_ils, mock_baton):
        mock_baton.return_value = out = json.loads(TEST_BATON_JSON, cls=MetadataJSONDecoder)

        metadata = self.irods.get_metadata("/foo/bar")
        mock_ils.assert_called_once_with("/foo/bar")
        mock_baton.assert_called_once_with("/foo/bar")

        # This doesn't prove much, but we've tested elsewhere that the
        # baton output deserialisation works as expected
        self.assertEqual(metadata, out)


if __name__ == "__main__":
    unittest.main()
