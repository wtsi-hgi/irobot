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
from base64 import b64encode
from datetime import timedelta

import irobot.authentication._http as http
import irobot.authentication.basic as basic
from irobot.authentication.parser import HTTPAuthMethod
from irobot.config import BasicAuthConfig
from irobot.config._tree_builder import ConfigValue
from irobot.test.async import async_test


@patch("irobot.authentication._http.Timer", spec=True)
class TestHTTPBasicAuthHandler(unittest.TestCase):
    def setUp(self):
        self.config = BasicAuthConfig()
        self.config.add_value("url", ConfigValue("foo", str))
        self.config.add_value("cache", ConfigValue(123, timedelta))

    def test_challenge(self, *args):
        auth = basic.HTTPBasicAuthHandler(self.config)
        self.assertEqual(auth.www_authenticate, "Basic")

        self.config.add_value("realm", ConfigValue("foo", str))
        auth = basic.HTTPBasicAuthHandler(self.config)
        self.assertEqual(auth.www_authenticate, "Basic realm=\"foo\"")

    def test_match_auth_method(self, *args):
        auth = basic.HTTPBasicAuthHandler(self.config)

        challenge_response = HTTPAuthMethod("Basic", payload="foo")
        self.assertTrue(auth.match_auth_method(challenge_response))

        challenge_response = HTTPAuthMethod("Basic")
        self.assertFalse(auth.match_auth_method(challenge_response))

        challenge_response = HTTPAuthMethod("Basic", params={"foo": "bar"})
        self.assertFalse(auth.match_auth_method(challenge_response))

        challenge_response = HTTPAuthMethod("foo")
        self.assertFalse(auth.match_auth_method(challenge_response))

    def test_set_handler_parameters(self, *args):
        auth = basic.HTTPBasicAuthHandler(self.config)

        challenge_response = HTTPAuthMethod("Basic", payload="bar")
        self.assertEqual(auth.set_handler_parameters(challenge_response),
                         http.HTTPValidatorParameters(url="foo", payload="Basic bar"))

    @async_test
    async def test_get_authenticated_user(self, *args):
        auth = basic.HTTPBasicAuthHandler(self.config)

        payload = b64encode(f"foo:bar".encode()).decode()
        challenge_response = HTTPAuthMethod("Basic", payload=payload)

        user = await auth.get_authenticated_user(challenge_response, None)
        self.assertEqual(user.user, "foo")


if __name__ == "__main__":
    unittest.main()
