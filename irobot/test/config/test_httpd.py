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
from ConfigParser import ParsingError

import irobot.config.httpd as httpd


class TestHTTPdConfig(unittest.TestCase):
    def test_bind_address_parsing(self):
        parse_bind_address = httpd._parse_bind_address

        self.assertRaises(ParsingError, parse_bind_address, "foo")
        self.assertRaises(ParsingError, parse_bind_address, "999.999.999.999")
        self.assertRaises(ParsingError, parse_bind_address, "0777.0777.0777.0777")
        self.assertRaises(ParsingError, parse_bind_address, str(2**32))
        self.assertEqual(parse_bind_address("222.173.190.239"), "222.173.190.239")
        self.assertEqual(parse_bind_address("3735928559"), "222.173.190.239")
        self.assertEqual(parse_bind_address("0xdeadbeef"), "222.173.190.239")
        self.assertEqual(parse_bind_address("0xDE.0xAD.0xBE.0xEF"), "222.173.190.239")
        self.assertEqual(parse_bind_address("0336.0255.0276.0357"), "222.173.190.239")

    def test_listening_port_parsing(self):
        parse_listening_port = httpd._parse_listening_port

        self.assertRaises(ValueError, parse_listening_port, "foo")
        self.assertRaises(ParsingError, parse_listening_port, "-1")
        self.assertRaises(ParsingError, parse_listening_port, "65536")
        self.assertEqual(parse_listening_port("1234"), 1234)

    def test_timeout_parsing(self):
        parse_timeout = httpd._parse_timeout

        self.assertRaises(ParsingError, parse_timeout, "foo")
        self.assertRaises(ParsingError, parse_timeout, "-1")
        self.assertEqual(parse_timeout("1000"), 1000)
        self.assertEqual(parse_timeout("1000ms"), 1000)
        self.assertEqual(parse_timeout("1000 ms"), 1000)
        self.assertEqual(parse_timeout("1s"), 1000)
        self.assertEqual(parse_timeout("1.1 s"), 1100)
        self.assertIsNone(parse_timeout("0"))
        self.assertIsNone(parse_timeout("0ms"))
        self.assertIsNone(parse_timeout("0s"))
        self.assertIsNone(parse_timeout("unlimited"))

    def test_authentication_parsing(self):
        parse_auth = httpd._parse_authentication

        self.assertRaises(ParsingError, parse_auth, "")
        self.assertItemsEqual(parse_auth("foo"), ["foo"])
        self.assertItemsEqual(parse_auth("foo,bar"), ["foo", "bar"])
        self.assertItemsEqual(parse_auth("fOo,BaR"), ["foo", "bar"])
        self.assertItemsEqual(parse_auth("foo,bar  ,    baz"), ["foo", "bar", "baz"])

    def test_instance(self):
        config = httpd.HTTPdConfig("0.0.0.0", "5000", "1000ms", "basic,foo, bar ,baz")

        self.assertEqual(config.bind_address(), "0.0.0.0")
        self.assertEqual(config.listen(), 5000)
        self.assertEqual(config.timeout(), 1000)
        self.assertItemsEqual(config.authentication(), ["basic", "foo", "bar", "baz"])


if __name__ == "__main__":
    unittest.main()
