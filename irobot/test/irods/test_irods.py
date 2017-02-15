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
from unittest.mock import MagicMock, call

import irobot.irods.irods as irods
import irobot.common.listener as listener
from irobot.config.irods import iRODSConfig


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


irods.baton = MagicMock(return_value=TEST_DATAOBJECT_METADATA)
irods.ils = MagicMock()
irods.iget = MagicMock()


class ListenerInternals(object):
    def __init__(self, original):
        self._orig = original
        self._orig_check_listener = original._check_listener
        self._orig_broadcast_time = original._broadcast_time

    def mock(self):
        self._orig._check_listener = MagicMock()
        self._orig._broadcast_time = MagicMock(return_value=1234)

    def reset(self):
        self._orig._check_listener = self._orig_check_listener
        self._orig._broadcast_time = self._orig_broadcast_time


class TestExists(unittest.TestCase):
    def tearDown(self):
        irods.ils.reset_mock()
        irods.ils.side_effect = None

    def test_exists_pass(self):
        irods._exists("/foo/bar")
        irods.ils.assert_called_once_with("/foo/bar")

    def test_exists_fail(self):
        irods.ils.side_effect = CalledProcessError(1, None, None)
        self.assertRaises(IOError, irods._exists, "/foo/bar")


class TestiRODS(unittest.TestCase):
    def setUp(self):
        config = iRODSConfig(max_connections="1")
        self.irods = irods.iRODS(config)
        self.listener_interals = ListenerInternals(listener)
    
    def tearDown(self):
        self.listener_interals.reset()

        irods.baton.reset_mock()
        irods.ils.reset_mock()
        irods.ils.side_effect = None
        irods.iget.reset_mock()
        irods.iget.side_effect = None

        # Stop the thread runner
        self.irods._running = False
        self.irods._runner.join()

    def test_destructor(self):
        self.irods.__del__()
        self.assertFalse(self.irods._running)

    def test_enqueue_dataobject(self):
        # Override listener internals
        self.listener_interals.mock()

        # Stop the thread runner
        self.irods._running = False
        self.irods._runner.join()

        _listener = MagicMock()
        self.irods.add_listener(_listener)

        self.irods.get_dataobject("/foo/bar", "/quux/xyzzy")
        _listener.assert_called_once_with(1234, irods.IGET_QUEUED, "/foo/bar")
        self.assertEqual(len(self.irods._iget_queue), 1)
        self.assertEqual(self.irods._iget_queue.pop(), ("/foo/bar", "/quux/xyzzy"))

    def test_iget_pool(self):
        # Stop the thread runner...
        self.irods._running = False
        self.irods._runner.join()

        _old_thread, irods.Thread = irods.Thread, MagicMock()
        def _stop_running(*args, **kwargs):
            self.irods._running = False
        irods.Thread().start = _stop_running

        # ...start it up again with two items in the queue
        self.irods._iget_queue.append(("/foo/bar", "/quux/xyzzy"))
        self.irods._iget_queue.append(("/another/test", "/fizz/buzz"))
        self.irods._running = True
        self.irods._thread_runner()

        irods.Thread.assert_has_calls([
            call(args=("/foo/bar", "/quux/xyzzy"), target=self.irods._iget)
        ])

        # Our instance only allows one iget at a time (i.e.,
        # max_connections=1), therefore -- as the runner is forcefully
        # terminated -- there should still be an element in the queue
        # FIXME This will be true regardless of the resource locking
        self.assertEqual(len(self.irods._iget_queue), 1)
        self.assertEqual(self.irods._iget_queue.pop(), ("/another/test", "/fizz/buzz"))

        irods.Thread = _old_thread

    def test_iget_pass(self):
        # Override listener internals
        self.listener_interals.mock()

        _listener = MagicMock()
        self.irods.add_listener(_listener)

        self.irods._iget("/foo/bar", "/quux/xyzzy")
        irods.iget.assert_called_once_with("/foo/bar", "/quux/xyzzy")
        _listener.assert_has_calls([
            call(1234, irods.IGET_STARTED, "/foo/bar"),
            call(1234, irods.IGET_FINISHED, "/foo/bar")
        ])

    def test_iget_fail(self):
        # Override listener internals
        self.listener_interals.mock()

        _listener = MagicMock()
        self.irods.add_listener(_listener)

        irods.iget.side_effect = CalledProcessError(1, "foo", "bar")

        self.irods._iget("/foo/bar", "/quux/xyzzy")
        irods.iget.assert_called_once_with("/foo/bar", "/quux/xyzzy")
        _listener.assert_has_calls([
            call(1234, irods.IGET_STARTED, "/foo/bar"),
            call(1234, irods.IGET_FAILED, "/foo/bar")
        ])

    def test_get_metadata(self):
        avu_metadata, fs_metadata = self.irods.get_metadata("/foo/bar")
        irods.ils.assert_called_once_with("/foo/bar")
        irods.baton.assert_called_once_with("/foo/bar")

        self.assertEqual(avu_metadata, TEST_DATAOBJECT_METADATA["avus"])

        for k in ["checksum", "size", "access", "timestamps"]:
            self.assertEqual(fs_metadata[k], TEST_DATAOBJECT_METADATA[k])


if __name__ == "__main__":
    unittest.main()
