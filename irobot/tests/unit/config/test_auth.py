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

import irobot.config._auth as auth


class TestArvadosAuthConfig(unittest.TestCase):
    def test_canon_hostname(self):
        canon_hostname = auth.arvados_hostname

        self.assertEqual(canon_hostname("127.0.0.1"), "127.0.0.1")
        self.assertEqual(canon_hostname("foo.bar"), "foo.bar")
        self.assertRaises(ParsingError, canon_hostname, "-not-cool")

    def test_canon_version(self):
        canon_version = auth.arvados_version

        self.assertEqual(canon_version("v1"), "v1")
        self.assertRaises(ParsingError, canon_version, "foo")


class TestBasicAuthConfig(unittest.TestCase):
    def test_canon_url(self):
        canon_url = auth.url

        self.assertEqual(canon_url("127.0.0.1:5000/foo/bar"), "http://127.0.0.1:5000/foo/bar")
        self.assertEqual(canon_url("https://foo.bar/quux"), "https://foo.bar/quux")
        self.assertRaises(ParsingError, canon_url, "-not-cool")


if __name__ == "__main__":
    unittest.main()
