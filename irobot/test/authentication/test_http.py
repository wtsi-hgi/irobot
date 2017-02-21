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
from datetime import datetime, timedelta
from threading import Timer
from typing import Any

from requests import HTTPError, Response, Request, Session

import irobot.authentication._base as base
import irobot.authentication._http as http
from irobot.config._base import BaseConfig


class _MockHTTPAuthentication(http.HTTPAuthHandler):
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


class TestHTTPAuthenticationHandler(unittest.TestCase):
    def setUp(self):
        self._old_timer, http.Timer = http.Timer, MagicMock(spec=Timer)
        self._old_response, http.Response = http.Response, MagicMock(spec=Response)
        self._old_request, http.Request = http.Request, MagicMock(spec=Request)
        self._old_session, http.Session = http.Session, MagicMock(spec=Session)
        self._old_datetime, base.datetime = base.datetime, MagicMock(spec=datetime)

        self.config_cache = _MockHTTPAuthConfig(timedelta(minutes=10))
        self.config_nocache = _MockHTTPAuthConfig(None)

    def tearDown(self):
        http.Timer = self._old_timer
        http.Response = self._old_response
        http.Request = self._old_request
        http.Session = self._old_session
        base.datetime = self._old_datetime

    def test_creation(self):
        auth_cache = _MockHTTPAuthentication(self.config_cache)
        self.assertTrue(hasattr(auth_cache, "_cache"))

        auth_nocache = _MockHTTPAuthentication(self.config_nocache)
        self.assertFalse(hasattr(auth_nocache, "_cache"))

    def test_shutdown_with_cache(self):
        auth = _MockHTTPAuthentication(self.config_cache)

        auth._cleanup_timer.is_alive.return_value = True
        auth.__del__()

        auth._cleanup_timer.cancel.assert_called_once()

    def test_cleanup(self):
        auth = _MockHTTPAuthentication(self.config_cache)

        validation_time = base.datetime.utcnow.return_value = datetime.utcnow()
        auth._cache["foo"] = http.AuthenticatedUser("foo")

        auth._cleanup()
        self.assertIn("foo", auth._cache)
        self.assertEqual(auth._cache["foo"].user, "foo")
        self.assertEqual(auth._cache["foo"].authenticated, validation_time)

        base.datetime.utcnow.return_value = validation_time + timedelta(minutes=11)
        auth._cleanup()
        self.assertEqual(auth._cache, {})

    def test_request_validator(self):
        auth = _MockHTTPAuthentication(self.config_cache)

        http.Session().send().status_code = 200
        self.assertIsInstance(auth._validate_request(http.Request()), MagicMock)

        http.Session().send().status_code = 401
        self.assertIsNone(auth._validate_request(http.Request()))

        http.Session().send().status_code = 500
        http.Session().send().raise_for_status.side_effect = HTTPError
        self.assertRaises(HTTPError, auth._validate_request, http.Request())

    def test_authenticate(self):
        auth = _MockHTTPAuthentication(self.config_cache)

        self.assertIsNone(auth.authenticate("fail"))

        validation_time = base.datetime.utcnow.return_value = datetime.utcnow()
        http.Session().send().status_code = 200
        self.assertEqual(auth._cache, {})
        self.assertTrue(auth.authenticate("foo"))  # Authenticated
        self.assertIn("foo", auth._cache)
        self.assertEqual(auth._cache["foo"].user, "foo")
        self.assertEqual(auth._cache["foo"].authenticated, validation_time)
        self.assertTrue(auth.authenticate("foo"))  # Authenticated from cache

        # Invalidate cache and now fail authentication
        base.datetime.utcnow.return_value = validation_time + timedelta(minutes=11)
        http.Session().send().status_code = 403
        self.assertFalse(auth.authenticate("foo"))


if __name__ == "__main__":
    unittest.main()
