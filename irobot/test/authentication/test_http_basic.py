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
from datetime import datetime, timedelta
from threading import Timer
from unittest.mock import MagicMock

import requests

import irobot.authentication.http_basic as http_basic
from irobot.config.authentication import BasicAuthConfig


class TestBasicAuthParser(unittest.TestCase):
    def setUp(self):
        self.creds = ("foo", "bar")
        self.basic_auth = "Basic %s" % b64encode("{}:{}".format(*self.creds).encode())

    def test_good_parse(self):
        parse_auth = http_basic._parse_auth_header
        self.assertEqual(parse_auth(self.basic_auth), self.creds)

    def test_bad_parse(self):
        parse_auth = http_basic._parse_auth_header
        self.assertRaises(ValueError, parse_auth, "foo bar")


class TestHTTPBasicAuthHandler(unittest.TestCase):
    def setUp(self):
        self._old_timer, http_basic.Timer = http_basic.Timer, MagicMock(spec=Timer)
        self._old_datetime, http_basic.datetime = http_basic.datetime, MagicMock(spec=datetime)
        self._old_requests, http_basic.requests = http_basic.requests, MagicMock(spec=requests)

        self.config = BasicAuthConfig("sanger.ac.uk", "10 min")
        self.config_nocache = BasicAuthConfig("sanger.ac.uk", "never")

    def tearDown(self):
        http_basic.Timer = self._old_timer
        http_basic.datetime = self._old_datetime
        http_basic.requests = self._old_requests

    def test_expiry(self):
        auth = http_basic.HTTPBasicAuthHandler(self.config)

        validation_time = datetime.utcnow()

        http_basic.datetime.utcnow.return_value = validation_time
        self.assertFalse(auth._has_expired(validation_time))

        http_basic.datetime.utcnow.return_value = validation_time + timedelta(minutes=11)
        self.assertTrue(auth._has_expired(validation_time))

    def test_cleanup(self):
        auth = http_basic.HTTPBasicAuthHandler(self.config)

        validation_time = auth._cache["foo"] = datetime.utcnow()

        http_basic.datetime.utcnow.return_value = validation_time
        auth._cleanup()
        self.assertEqual(auth._cache, {"foo": validation_time})

        http_basic.datetime.utcnow.return_value = validation_time + timedelta(minutes=11)
        auth._cleanup()
        self.assertEqual(auth._cache, {})

    def test_startup(self):
        auth_cache = http_basic.HTTPBasicAuthHandler(self.config)
        self.assertTrue(hasattr(auth_cache, "_cache"))

        auth_nocache = http_basic.HTTPBasicAuthHandler(self.config_nocache)
        self.assertFalse(hasattr(auth_nocache, "_cache"))

    def test_shutdown_with_cache(self):
        auth = http_basic.HTTPBasicAuthHandler(self.config)

        auth._cleanup_timer.is_alive.return_value = True
        auth.__del__()

        auth._cleanup_timer.cancel.assert_called_once()

    def test_http_validator(self):
        auth = http_basic.HTTPBasicAuthHandler(self.config)

        http_basic.requests.get().status_code = 200
        self.assertTrue(auth._valid_auth_request("foo", "bar"))

        http_basic.requests.get().status_code = 401
        self.assertFalse(auth._valid_auth_request("foo", "bar"))

        http_basic.requests.get().status_code = 500
        http_basic.requests.get().raise_for_status.side_effect = requests.HTTPError()
        self.assertRaises(requests.HTTPError, auth._valid_auth_request, "foo", "bar")

    def test_public_validator(self):
        auth = http_basic.HTTPBasicAuthHandler(self.config)

        self.assertFalse(auth.validate("foo bar"))

        basic_auth = "Basic %s" % b64encode("foo:bar".encode())
        validation_time = http_basic.datetime.utcnow.return_value = datetime.utcnow()
        http_basic.requests.get().status_code = 200
        self.assertEqual(auth._cache, {})
        self.assertTrue(auth.validate(basic_auth))  # Authenticated
        self.assertEqual(auth._cache, {"foo": validation_time})
        self.assertTrue(auth.validate(basic_auth))  # Authenticated from cache

        # Invalidate cache and now fail authentication
        http_basic.datetime.utcnow.return_value = validation_time + timedelta(minutes=11)
        http_basic.requests.get().status_code = 403
        self.assertFalse(auth.validate(basic_auth))


if __name__ == "__main__":
    unittest.main()
