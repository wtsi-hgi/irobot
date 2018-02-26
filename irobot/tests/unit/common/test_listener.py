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
from unittest.mock import MagicMock, patch

from irobot.common.listenable import Listenable, _broadcast_time


class TestListenableInternals(unittest.TestCase):
    @patch("irobot.common.listenable.datetime", spec=True)
    def test_broadcast_time(self, mock_datetime):
        _broadcast_time()
        mock_datetime.utcnow.assert_called_once()


class TestListenable(unittest.TestCase):
    def test_add_listener(self):
        l = Listenable()
        self.assertEqual(len(l.listeners), 0)

        _listener = MagicMock()
        l.add_listener(_listener)

        self.assertEqual(len(l.listeners), 1)
        self.assertEqual(l.listeners.pop(), _listener)

    @patch("irobot.common.listenable._broadcast_time", spec=True)
    def test_broadcast(self, mock_broadcast_time):
        l = Listenable()

        _listener = MagicMock()
        l.add_listener(_listener)
        l.broadcast("foo", "bar", quux="xyzzy")

        _listener.assert_called_once_with(mock_broadcast_time(), "foo", "bar", quux="xyzzy")


if __name__ == "__main__":
    unittest.main()
