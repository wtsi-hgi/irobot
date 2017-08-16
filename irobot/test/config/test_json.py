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
from datetime import datetime, timedelta
from typing import List

from irobot.config._json import ConfigJSONEncoder
from irobot.config._tree_builder import Configuration, ConfigValue


def _split(s:str) -> List:
    return s.split(",")

def _t(s:str) -> datetime:
    return datetime.utcfromtimestamp(int(s))

def _dt(s:str) -> timedelta:
    return timedelta(hours=int(s))

def _none(s:str) -> None:
    return None

def _unknown(s:str) -> object:
    class _foo(object):
        pass

    return _foo()


class TestJSONEncoder(unittest.TestCase):
    def setUp(self):
        self.encoder = ConfigJSONEncoder()

    def test_traversal(self):
        default = self.encoder.default

        config = Configuration()
        children = [Configuration(), Configuration()]
        for i, child in enumerate(children):
            config.add_config(f"config{i}", child)

        self.assertEqual(default(config), {"config0": children[0], "config1": children[1]})

    def test_leaf_encoding(self):
        default = self.encoder.default

        self.assertEqual(default(ConfigValue("foo", str)), "foo")
        self.assertEqual(default(ConfigValue("123", int)), 123)
        self.assertEqual(default(ConfigValue("1.23", float)), 1.23)
        self.assertEqual(default(ConfigValue("foo", bool)), True)
        self.assertEqual(default(ConfigValue("a,b,c", _split)), ["a", "b", "c"])
        self.assertEqual(default(ConfigValue("0", _t)), "1970-01-01T00:00:00Z+0000")
        self.assertEqual(default(ConfigValue("1", _dt)), "1:00:00")
        self.assertEqual(default(ConfigValue("none", _none)), None)
        self.assertEqual(default(ConfigValue("something", _none)), "something")
        self.assertEqual(default(ConfigValue("something", _unknown)), "something")
        self.assertRaises(TypeError, default, timedelta(1))


if __name__ == "__main__":
    unittest.main()
