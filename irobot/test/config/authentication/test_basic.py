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

import irobot.config.authentication.basic as basic_conf


class TestBasicAuthConfig(unittest.TestCase):
    def test_url(self):
        get_url = lambda x: basic_conf.BasicAuthConfig(x, "never").url

        self.assertEqual(get_url("127.0.0.1:5000/foo/bar"), "http://127.0.0.1:5000/foo/bar")
        self.assertEqual(get_url("https://foo.bar/quux"), "https://foo.bar/quux")
        self.assertRaises(ParsingError, get_url, "-not-cool")

    def test_bad_duration(self):
        self.assertRaises(ParsingError, basic_conf.BasicAuthConfig, "sanger.ac.uk", "foo")

    def test_instance(self):
        config = basic_conf.BasicAuthConfig("sanger.ac.uk", "never")

        self.assertEqual(config.url, "http://sanger.ac.uk")
        self.assertIsNone(config.cache)


if __name__ == "__main__":
    unittest.main()
