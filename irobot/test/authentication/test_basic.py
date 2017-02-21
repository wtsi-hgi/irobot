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
from base64 import b64encode
from unittest.mock import MagicMock
from threading import Timer

import requests

import irobot.authentication._http as http
import irobot.authentication.basic as basic
from irobot.config.authentication import BasicAuthConfig


class TestHTTPBasicAuthHandler(unittest.TestCase):
    def setUp(self):
        self._old_timer, http.Timer = http.Timer, MagicMock(spec=Timer)
        self.config = MagicMock(spec=BasicAuthConfig)

    def tearDown(self):
        http.Timer = self._old_timer

    def test_parser(self):
        auth = basic.HTTPBasicAuthHandler(self.config)

        creds = user, password = ("foo", "bar")
        payload = f"{user}:{password}".encode()
        basic_auth = "Basic {}".format(b64encode(payload).decode())

        parse_auth = auth.parse_auth_header
        self.assertEqual(parse_auth(basic_auth), creds)
        self.assertRaises(ValueError, parse_auth, "foo bar")

    def test_request(self):
        auth = basic.HTTPBasicAuthHandler(self.config)
        req = auth.auth_request("foo", "bar")

        self.assertEqual(req.auth, ("foo", "bar"))
        self.assertEqual(auth.get_user(req, None), "foo")


if __name__ == "__main__":
    unittest.main()
