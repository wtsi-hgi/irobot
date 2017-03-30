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
from subprocess import CalledProcessError
from unittest.mock import MagicMock, call, patch

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
        # Stop the thread runner
        self.irods._running = False
        self.irods._runner.join()

    def test_destructor(self):
        self.irods.__del__()
        self.assertFalse(self.irods._running)

    @patch("irobot.irods.irods.ils", spec=True)
    @patch("irobot.common.listenable._broadcast_time", spec=True)
    def test_enqueue_dataobject(self, mock_broadcast_time, *args):
        # Stop the thread runner
        self.irods._running = False
        self.irods._runner.join()

        _listener = MagicMock()
        self.irods.add_listener(_listener)

        self.irods.get_dataobject("/foo/bar", "/quux/xyzzy")
        _listener.assert_called_once_with(mock_broadcast_time(), iGetStatus.queued, "/foo/bar")
        self.assertEqual(len(self.irods._iget_queue), 1)
        self.assertEqual(self.irods._iget_queue.pop(), ("/foo/bar", "/quux/xyzzy"))

    def test_iget_pool(self):
        # Stop the thread runner...
        self.irods._running = False
        self.irods._runner.join()

        with patch("irobot.irods.irods.Thread") as mock_thread:
            def _stop_running(*args, **kwargs):
                self.irods._running = False
            mock_thread().start = _stop_running

            # ...start it up again with two items in the queue
            self.irods._iget_queue.append(("/foo/bar", "/quux/xyzzy"))
            self.irods._iget_queue.append(("/another/test", "/fizz/buzz"))
            self.irods._running = True
            self.irods._thread_runner()

            mock_thread.assert_has_calls([
                call(args=("/foo/bar", "/quux/xyzzy"), target=self.irods._iget)
            ])

            # Our instance only allows one iget at a time (i.e.,
            # max_connections=1), therefore -- as the runner is
            # forcefully terminated -- there should still be an element
            # in the queue
            # FIXME This will be true regardless of the resource locking
            self.assertEqual(len(self.irods._iget_queue), 1)
            self.assertEqual(self.irods._iget_queue.pop(), ("/another/test", "/fizz/buzz"))

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
