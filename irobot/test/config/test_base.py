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

from irobot.config._base import BaseConfig


class _FooConfig(BaseConfig):
    def foo(self):
        return "bar"

    def quux(self):
        return "xyzzy"

    def _moo(self):
        return "quack"


class TestBaseConfig(unittest.TestCase):
    def setUp(self):
        self.config = _FooConfig()

    def test_str(self):
        s = str(self.config)
        self.assertRegex(s, r"foo: bar")
        self.assertRegex(s, r"quux: xyzzy")
        self.assertNotRegexpMatches(s, r"_moo: quack")


if __name__ == "__main__":
    unittest.main()
