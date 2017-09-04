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

from irobot.authentication.parser import AuthHandler, ParseError, auth_parser


class TestAuthParser(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(auth_parser("Basic"),
                         [AuthHandler("Basic")])

        self.assertEqual(auth_parser("foo,bar  , quux"),
                         [AuthHandler("foo"), AuthHandler("bar"), AuthHandler("quux")])

    def test_payload(self):
        self.assertEqual(auth_parser("foo quux"),
                         [AuthHandler("foo", payload="quux")])

    def test_params(self):
        self.assertEqual(auth_parser("foo bar=quux, quux xyzzy=baz, foo=\"abc123\""),
                         [AuthHandler("foo", params={"bar":"quux"}),
                          AuthHandler("quux", params={"xyzzy":"baz", "foo":"\"abc123\""})])


if __name__ == "__main__":
    unittest.main()
