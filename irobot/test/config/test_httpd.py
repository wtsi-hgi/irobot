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
from configparser import ParsingError
from datetime import timedelta

import irobot.config.httpd as httpd


class TestHTTPdConfig(unittest.TestCase):
    def test_listening_port_parsing(self):
        canon_listening_port = httpd._canon_listening_port

        self.assertRaises(ValueError, canon_listening_port, "foo")
        self.assertRaises(ParsingError, canon_listening_port, "-1")
        self.assertRaises(ParsingError, canon_listening_port, "65536")
        self.assertEqual(canon_listening_port("1234"), 1234)

    def test_timeout_parsing(self):
        canon_timeout = httpd._canon_timeout

        self.assertRaises(ParsingError, canon_timeout, "foo")
        self.assertRaises(ParsingError, canon_timeout, "-1")
        self.assertRaises(ParsingError, canon_timeout, "0")
        self.assertRaises(ParsingError, canon_timeout, "0ms")
        self.assertRaises(ParsingError, canon_timeout, "0s")
        self.assertEqual(canon_timeout("1000"), timedelta(milliseconds=1000))
        self.assertEqual(canon_timeout("1000ms"), timedelta(milliseconds=1000))
        self.assertEqual(canon_timeout("1000 ms"), timedelta(milliseconds=1000))
        self.assertEqual(canon_timeout("1s"), timedelta(milliseconds=1000))
        self.assertEqual(canon_timeout("1.1 s"), timedelta(milliseconds=1100))
        self.assertIsNone(canon_timeout("unlimited"))

    def test_authentication_parsing(self):
        canon_auth = httpd._canon_authentication

        self.assertRaises(ParsingError, canon_auth, "")
        self.assertEqual(canon_auth("foo"), ["foo"])
        self.assertEqual(canon_auth("foo,bar"), ["foo", "bar"])
        self.assertEqual(canon_auth("fOo,BaR"), ["foo", "bar"])
        self.assertEqual(canon_auth("foo,bar  ,    baz"), ["foo", "bar", "baz"])

    def test_bad_bind_address(self):
        self.assertRaises(ParsingError, httpd.HTTPdConfig, "foo", "5000", "1000ms", "basic")

    def test_instance(self):
        config = httpd.HTTPdConfig("0.0.0.0", "5000", "1000ms", "basic,foo, bar ,baz")

        self.assertEqual(config.bind_address, "0.0.0.0")
        self.assertEqual(config.listen, 5000)
        self.assertEqual(config.timeout, timedelta(milliseconds=1000))
        self.assertEqual(config.authentication, ["basic", "foo", "bar", "baz"])


if __name__ == "__main__":
    unittest.main()
