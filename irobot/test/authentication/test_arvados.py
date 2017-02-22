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
from threading import Timer

from requests import Response

import irobot.authentication._http as http
import irobot.authentication.arvados as arv
from irobot.config.authentication import ArvadosAuthConfig


class TestArvadosAuthHandler(unittest.TestCase):
    def setUp(self):
        self._old_timer, http.Timer = http.Timer, MagicMock(spec=Timer)
        self.config = ArvadosAuthConfig("foo", "v1", "10 min")

    def tearDown(self):
        http.Timer = self._old_timer

    def test_parser(self):
        auth = arv.ArvadosAuthHandler(self.config)

        self.assertEqual(auth.parse_auth_header("Arvados abc123"), ("abc123",))
        self.assertRaises(ValueError, auth.parse_auth_header, "foo bar")

    def test_request(self):
        auth = arv.ArvadosAuthHandler(self.config)
        req = auth.auth_request("abc123")

        self.assertEquals(req.url, "https://foo/arvados/v1/users/current")
        self.assertEquals(req.headers["Authorization"], "OAuth2 abc123")

    def test_get_user(self):
        auth = arv.ArvadosAuthHandler(self.config)

        res = MagicMock(spec=Response)

        res.status_code = 200
        res.json.return_value = {"username": "foo"}
        self.assertEquals(auth.get_user(None, res), "foo")

        res.status_code = "foo"
        self.assertRaises(ValueError, auth.get_user, None, res)

if __name__ == "__main__":
    unittest.main()