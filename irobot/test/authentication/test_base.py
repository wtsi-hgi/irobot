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
from unittest.mock import patch
from datetime import datetime, timedelta

import irobot.authentication._base as base


@patch("irobot.authentication._base.datetime", spec=True)
class TestAuthenticatedUser(unittest.TestCase):
    def test_properties(self, mock_datetime):
        validation_time = mock_datetime.utcnow.return_value = datetime.utcnow()
        user = base.AuthenticatedUser("foo")

        self.assertEqual(user.user, "foo")
        self.assertEqual(user.authenticated, validation_time)

    def test_validity(self, mock_datetime):
        validation_time = datetime.utcnow()

        mock_datetime.utcnow.return_value = validation_time
        user = base.AuthenticatedUser("foo")
        self.assertTrue(user.valid(timedelta(minutes=10)))

        mock_datetime.utcnow.return_value = validation_time + timedelta(minutes=11)
        self.assertFalse(user.valid(timedelta(minutes=10)))

        self.assertFalse(user.valid(None))


if __name__ == "__main__":
    unittest.main()
