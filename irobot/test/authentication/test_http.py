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
from threading import Timer
from typing import Any

from requests import HTTPError, Response, Request, Session

import irobot.authentication._base as base
import irobot.authentication._http as http
from irobot.config._base import BaseConfig


class _MockHTTPAuthentication(http.HTTPAuthHandler):
    @property
    def www_authenticate(self) -> str:
        return "Mock"

    def parse_auth_header(self, auth_header:str) -> str:
        if auth_header == "fail":
            raise ValueError()

        return auth_header

    def auth_request(self, *args) -> http.Request:
        return http.Request()

    def get_user(self, req:http.Request, res:http.Response) -> str:
        return "foo"


class _MockHTTPAuthConfig(BaseConfig):
    def __init__(self, cache):
        self.cache = cache


@patch("irobot.authentication._base.datetime", spec=True)
@patch("irobot.authentication._http.Session", spec=True)
@patch("irobot.authentication._http.Request", spec=True)
@patch("irobot.authentication._http.Response", spec=True)
@patch("irobot.authentication._http.Timer", spec=True)
class TestHTTPAuthenticationHandler(unittest.TestCase):
    def setUp(self):
        self.config_cache = _MockHTTPAuthConfig(timedelta(minutes=10))
        self.config_nocache = _MockHTTPAuthConfig(None)

    def test_creation(self, *args):
        auth_cache = _MockHTTPAuthentication(self.config_cache)
        self.assertTrue(hasattr(auth_cache, "_cache"))

        auth_nocache = _MockHTTPAuthentication(self.config_nocache)
        self.assertFalse(hasattr(auth_nocache, "_cache"))

    def test_shutdown_with_cache(self, *args):
        auth = _MockHTTPAuthentication(self.config_cache)

        auth._cleanup_timer.is_alive.return_value = True
        auth.__del__()

        auth._cleanup_timer.cancel.assert_called_once()

    def test_cleanup(self, mock_timer, mock_response, mock_request, mock_session, mock_datetime):
        auth = _MockHTTPAuthentication(self.config_cache)

        validation_time = mock_datetime.utcnow.return_value = datetime.utcnow()
        auth._cache["foo"] = http.AuthenticatedUser("foo")

        auth._cleanup()
        self.assertIn("foo", auth._cache)
        self.assertEqual(auth._cache["foo"].user, "foo")
        self.assertEqual(auth._cache["foo"].authenticated, validation_time)

        mock_datetime.utcnow.return_value = validation_time + timedelta(minutes=11)
        auth._cleanup()
        self.assertEqual(auth._cache, {})

    def test_request_validator(self, mock_timer, mock_response, mock_request, mock_session, mock_datetime):
        auth = _MockHTTPAuthentication(self.config_cache)

        mock_session().send().status_code = 200
        self.assertIsInstance(auth._validate_request(mock_request()), MagicMock)

        mock_session().send().status_code = 401
        self.assertIsNone(auth._validate_request(mock_request()))

        mock_session().send().status_code = 500
        mock_session().send().raise_for_status.side_effect = HTTPError
        self.assertRaises(HTTPError, auth._validate_request, mock_request())

    def test_authenticate(self, mock_timer, mock_response, mock_request, mock_session, mock_datetime):
        auth = _MockHTTPAuthentication(self.config_cache)

        self.assertIsNone(auth.authenticate("fail"))

        validation_time = mock_datetime.utcnow.return_value = datetime.utcnow()
        mock_session().send().status_code = 200
        self.assertEqual(auth._cache, {})
        self.assertTrue(auth.authenticate("foo"))  # Authenticated
        self.assertIn("foo", auth._cache)
        self.assertEqual(auth._cache["foo"].user, "foo")
        self.assertEqual(auth._cache["foo"].authenticated, validation_time)
        self.assertTrue(auth.authenticate("foo"))  # Authenticated from cache

        # Invalidate cache and now fail authentication
        mock_datetime.utcnow.return_value = validation_time + timedelta(minutes=11)
        mock_session().send().status_code = 403
        self.assertFalse(auth.authenticate("foo"))


if __name__ == "__main__":
    unittest.main()
