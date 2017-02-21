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

import irobot.config.authentication.arvados as arv_conf


class TestArvadosAuthConfig(unittest.TestCase):
    def test_canon_hostname(self):
        canon_hostname = arv_conf._canon_hostname

        self.assertEqual(canon_hostname("127.0.0.1"), "127.0.0.1")
        self.assertEqual(canon_hostname("foo.bar"), "foo.bar")
        self.assertRaises(ParsingError, canon_hostname, "-not-cool")

    def test_canon_version(self):
        canon_version = arv_conf._canon_version

        self.assertEqual(canon_version("v1"), "v1")
        self.assertRaises(ParsingError, canon_version, "foo")

    def test_bad_duration(self):
        self.assertRaises(ParsingError, arv_conf.ArvadosAuthConfig, "sanger.ac.uk", "v1", "foo")

    def test_instance(self):
        config = arv_conf.ArvadosAuthConfig("api.arvados.example", "v1", "never")

        self.assertEqual(config.api_host, "api.arvados.example")
        self.assertEqual(config.api_version, "v1")
        self.assertEqual(config.api_base_url, "https://api.arvados.example/arvados/v1")
        self.assertIsNone(config.cache)


if __name__ == "__main__":
    unittest.main()
