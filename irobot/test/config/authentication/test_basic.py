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
from unittest.mock import MagicMock

import requests

import irobot.config.authentication.basic as basic_conf


class TestBasicAuthConfig(unittest.TestCase):
    def setUp(self):
        self._old_requests_head, basic_conf.requests.head = basic_conf.requests.head, MagicMock()

    def tearDown(self):
        basic_conf.requests.head = self._old_requests_head

    def test_parse_bad_url(self):
        parse_url = basic_conf._parse_url
        basic_conf.requests.head = self._old_requests_head
        self.assertRaises(ParsingError, parse_url, "foo")

    def test_parse_timeout_url(self):
        parse_url = basic_conf._parse_url
        basic_conf.requests.head.side_effect = requests.Timeout
        self.assertRaises(ParsingError, parse_url, "foo")

    def test_parse_good_url(self):
        parse_url = basic_conf._parse_url

        self.assertEqual(parse_url("http://www.sanger.ac.uk"), "http://www.sanger.ac.uk")
        self.assertEqual(parse_url("sanger.ac.uk"), "http://sanger.ac.uk")

    def test_bad_duration(self):
        self.assertRaises(ParsingError, basic_conf.BasicAuthConfig, "sanger.ac.uk", "foo")

    def test_instance(self):
        config = basic_conf.BasicAuthConfig("sanger.ac.uk", "never")

        self.assertEqual(config.url(), "http://sanger.ac.uk")
        self.assertIsNone(config.cache())


if __name__ == "__main__":
    unittest.main()
