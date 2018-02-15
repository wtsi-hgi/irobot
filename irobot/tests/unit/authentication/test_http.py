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
from datetime import datetime, timedelta
from unittest.mock import patch

from aiohttp import ClientResponseError
from aioresponses import aioresponses

import irobot.authentication._http as http
from irobot.authentication._base import AuthenticatedUser
from irobot.authentication.parser import HTTPAuthMethod
from irobot.config import Configuration
from irobot.config._tree_builder import ConfigValue
from irobot.tests.unit.async import async_test


class _MockHTTPAuthConfig(Configuration):
    def __init__(self, cache):
        super().__init__()
        self.add_value("cache", ConfigValue(cache, lambda x: x))


_CONFIG_CACHE = _MockHTTPAuthConfig(timedelta(minutes=10))
_CONFIG_NOCACHE = _MockHTTPAuthConfig(None)


class _MockHTTPAuthenticator(http.BaseHTTPAuthHandler):
    @property
    def www_authenticate(self):
        return "Mock"

    def match_auth_method(self, challenge_response):
        return (challenge_response.auth_method == "foo")

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

    @async_test
    @aioresponses()
    async def test_request_validator(self, mock_response):
        auth = _MockHTTPAuthenticator(_CONFIG_NOCACHE)

        mock_url = "foo"
        params = http.HTTPValidatorParameters(mock_url, "bar")

        mock_response.get(mock_url, status=200)
        validation_response = await auth._validate_request(params)
        self.assertIsNotNone(validation_response)

        mock_response.get(mock_url, status=401)
        validation_response = await auth._validate_request(params)
        self.assertIsNone(validation_response)

        mock_response.get(mock_url, status=500)
        try:
            validation_response = await auth._validate_request(params)
        except Exception as e:
            self.assertIsInstance(e, ClientResponseError)

    @async_test
    @aioresponses()
    async def test_authenticate(self, mock_response):
        with patch("irobot.authentication._base.datetime", spec=True) as mock_datetime:
            # patch and aioresponses don't play nicely together as
            # decorators, so we use patch's context manager instead
            validation_time = mock_datetime.utcnow.return_value = datetime.utcnow()

            auth = _MockHTTPAuthenticator(_CONFIG_CACHE)

            auth_response = await auth.authenticate("this is a bad header")
            self.assertIsNone(auth_response)

            auth_response = await auth.authenticate("bar")
            self.assertIsNone(auth_response)

            mock_response.get("foo", status=401)
            auth_response = await auth.authenticate("foo")
            self.assertIsNone(auth_response)

            mock_response.get("foo", status=200)
            auth_response = await auth.authenticate("foo")
            self.assertEqual(auth_response.user, "Testy McTestface")

            # Run again to test it's coming from the cache
            mock_response.get("foo", status=200)
            auth_response = await auth.authenticate("foo")
            self.assertEqual(auth_response.user, "Testy McTestface")

            # Invalidate cache and go again
            mock_datetime.utcnow.return_value = validation_time + timedelta(minutes=11)
            mock_response.get("foo", status=200)
            auth_response = await auth.authenticate("foo")
            self.assertEqual(auth_response.user, "Testy McTestface")


if __name__ == "__main__":
    unittest.main()
