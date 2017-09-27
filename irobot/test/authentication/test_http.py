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
from datetime import datetime, timedelta

from aiohttp import ClientResponse

import irobot.authentication._http as http
from irobot.authentication._base import AuthenticatedUser
from irobot.authentication.parser import HTTPAuthMethod
from irobot.config import Configuration
from irobot.config._tree_builder import ConfigValue
from irobot.test.async import async_test


class _MockHTTPAuthConfig(Configuration):
    def __init__(self, cache):
        super().__init__()
        self.add_value("cache", ConfigValue(cache, lambda x: x))

_CONFIG_CACHE   = _MockHTTPAuthConfig(timedelta(minutes=10))
_CONFIG_NOCACHE = _MockHTTPAuthConfig(None)


class _MockHTTPAuthenticator(http.BaseHTTPAuthHandler):
    @property
    def www_authenticate(self):
        return "Mock"

    def match_auth_method(self, challenge_response):
        return True

    def set_handler_parameters(self, challenge_response):
        return http.HTTPValidatorParameters("foo", "bar")

    async def get_authenticated_user(self, challenge_response, auth_response):
        return AuthenticatedUser("Testy McTestface")


class TestHTTPAuthenticationHandler(unittest.TestCase):
    def test_constructor(self):
        auth_cache = _MockHTTPAuthenticator(_CONFIG_CACHE)
        self.assertTrue(hasattr(auth_cache, "_cache"))

        auth_nocache = _MockHTTPAuthenticator(_CONFIG_NOCACHE)
        self.assertFalse(hasattr(auth_nocache, "_cache"))

    @patch("irobot.authentication._http.Timer", spec=True)
    def test_cached_shutdown(self, *args):
        auth = _MockHTTPAuthenticator(_CONFIG_CACHE)

        auth._cleanup_timer.is_alive.return_value = True
        auth.__del__()

        auth._cleanup_timer.cancel.assert_called_once()

    @patch("irobot.authentication._base.datetime", spec=True)
    @patch("irobot.authentication._http.Timer", spec=True)
    def test_cache_cleanup(self, _mock_timer, mock_datetime):
        auth = _MockHTTPAuthenticator(_CONFIG_CACHE)

        auth_method = HTTPAuthMethod("foo")
        validation_time = mock_datetime.utcnow.return_value = datetime.utcnow()
        auth._cache[auth_method] = AuthenticatedUser("Testy McTestface")

        auth._cleanup()
        self.assertIn(auth_method, auth._cache)
        self.assertEqual(auth._cache[auth_method].user, "Testy McTestface")
        self.assertEqual(auth._cache[auth_method].authenticated, validation_time)

        mock_datetime.utcnow.return_value = validation_time + timedelta(minutes=11)
        auth._cleanup()
        self.assertEqual(auth._cache, {})

    # FIXME Patching doesn't seem to work for async code; the below test
    # is still trying to make the HTTP request, regardless of it
    # supposedly being mocked...

    # @async_test
    # @patch("irobot.authentication._http.ClientSession", spec=True)
    # async def test_request_validator(self, mock_client):
    #     mock_response = MagicMock(spec=ClientResponse)
    #     mock_client.request.return_value = mock_response
    #
    #     auth = _MockHTTPAuthenticator(_CONFIG_NOCACHE)
    #     params = http.HTTPValidatorParameters("foo", "bar")
    #
    #     mock_response.status = 200
    #     validation_response = await auth._validate_request(params)
    #     self.assertEqual(validation_response, mock_response)
    #
    # FIXME Same problem anticipated for test_authenticate...


if __name__ == "__main__":
    unittest.main()
