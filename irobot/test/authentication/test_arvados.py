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
from datetime import timedelta

from aiohttp import ClientResponse

import irobot.authentication._http as http
import irobot.authentication.arvados as arv
from irobot.authentication.parser import HTTPAuthMethod
from irobot.config import ArvadosAuthConfig
from irobot.config._tree_builder import ConfigValue
from irobot.test.async import async_test


@patch("irobot.authentication._http.Timer", spec=True)
class TestArvadosAuthHandler(unittest.TestCase):
    def setUp(self):
        self.config = ArvadosAuthConfig()
        self.config.add_value("api_host", ConfigValue("foo", str))
        self.config.add_value("api_version", ConfigValue("v1", str))
        self.config.add_value("api_base_url", ConfigValue("https://foo/arvados/v1", str))
        self.config.add_value("cache", ConfigValue(123, timedelta))

    def test_challenge(self, *args):
        auth = arv.ArvadosAuthHandler(self.config)
        self.assertEqual(auth.www_authenticate,
                         f"Bearer realm=\"{self.config.api_host}\"")

    def test_match_auth_method(self, *args):
        auth = arv.ArvadosAuthHandler(self.config)

        challenge_response = HTTPAuthMethod("Bearer", payload="foo")
        self.assertTrue(auth.match_auth_method(challenge_response))

        challenge_response = HTTPAuthMethod("Bearer")
        self.assertFalse(auth.match_auth_method(challenge_response))

        challenge_response = HTTPAuthMethod("Bearer", params={"foo": "bar"})
        self.assertFalse(auth.match_auth_method(challenge_response))

        challenge_response = HTTPAuthMethod("foo")
        self.assertFalse(auth.match_auth_method(challenge_response))

    def test_set_handler_parameters(self, *args):
        auth = arv.ArvadosAuthHandler(self.config)

        challenge_response = HTTPAuthMethod("Bearer", payload="bar")
        self.assertEqual(auth.set_handler_parameters(challenge_response),
                         http.HTTPValidatorParameters(
                             url=f"{self.config.api_base_url}/users/current",
                             payload="OAuth2 bar",
                             headers={"Accept": "application/json"}
                         ))

        self.config.api_version = "foo"
        self.assertRaises(RuntimeError, auth.set_handler_parameters, challenge_response)

    @async_test
    async def test_get_authenticated_user(self, *args):
        auth = arv.ArvadosAuthHandler(self.config)

        mock_auth_response = MagicMock(spec=ClientResponse)

        async def mock_json():
            return {"username": "foo"}

        mock_auth_response.status = 200
        mock_auth_response.json = mock_json
        user = await auth.get_authenticated_user(None, mock_auth_response)
        self.assertEqual(user.user, "foo")

        mock_auth_response.status = 123
        try:
            await auth.get_authenticated_user(None, mock_auth_response)
        except Exception as e:
            self.assertIsInstance(e, ValueError)


if __name__ == "__main__":
    unittest.main()
