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
from unittest.mock import MagicMock

import irobot.common.listener as listener


class TestListenerInternals(unittest.TestCase):
    def test_broadcast_time(self):
        _orig_datetime, listener.datetime = listener.datetime, MagicMock()

        listener._broadcast_time()
        listener.datetime.utcnow.assert_called_once()

        listener.datetime = _orig_datetime


class TestListener(unittest.TestCase):
    def setUp(self):
        self._orig_broadcast_time, listener._broadcast_time = listener._broadcast_time, MagicMock(return_value=1234)

    def tearDown(self):
        listener._broadcast_time = self._orig_broadcast_time

    def test_add_listener(self):
        l = listener.Listener()
        self.assertEqual(len(l._listeners), 0)

        _listener = MagicMock()
        l.add_listener(_listener)

        self.assertEqual(len(l._listeners), 1)
        self.assertEqual(l._listeners.pop(), _listener)

    def test_broadcast(self):
        l = listener.Listener()

        _listener = MagicMock()
        l.add_listener(_listener)
        l.broadcast("foo", "bar", quux="xyzzy")

        _listener.assert_called_once_with(1234, "foo", "bar", quux="xyzzy")


if __name__ == "__main__":
    unittest.main()
