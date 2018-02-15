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
from enum import Enum

from irobot.precache.db._adaptors_convertors import Adaptor, Convertor


class TestAdaptors(unittest.TestCase):
    def test_datetime(self):
        dt_adapt = Adaptor.datetime
        self.assertEqual(dt_adapt(datetime(1970, 1, 1)), 0)
        self.assertEqual(dt_adapt(datetime(1970, 1, 2)), 86400)

    def test_timedelta(self):
        d_adapt = Adaptor.timedelta
        self.assertEqual(d_adapt(timedelta(seconds=123)), 123.0)
        self.assertEqual(d_adapt(timedelta(days=1)), 86400.0)

    def test_enum(self):
        my_enum = Enum("my_enum", "foo bar quux")
        e_adapt = Adaptor.enum
        self.assertEqual(e_adapt(my_enum.foo), 1)
        self.assertEqual(e_adapt(my_enum.bar), 2)
        self.assertEqual(e_adapt(my_enum.quux), 3)


class TestConvertors(unittest.TestCase):
    def test_datetime(self):
        dt_conv = Convertor.datetime
        self.assertEqual(dt_conv(b"0"), datetime(1970, 1, 1))
        self.assertEqual(dt_conv(b"86400"), datetime(1970, 1, 2))

    def test_timedelta(self):
        d_conv = Convertor.timedelta
        self.assertEqual(d_conv(b"0"), timedelta(0))
        self.assertEqual(d_conv(b"1.23"), timedelta(seconds=1.23))
        self.assertEqual(d_conv(b"86400.0"), timedelta(days=1))

    def test_enum(self):
        my_enum = Enum("my_enum", "foo bar quux")
        e_conv = Convertor.enum_factory(my_enum)
        self.assertEqual(e_conv(b"1"), my_enum.foo)
        self.assertEqual(e_conv(b"2"), my_enum.bar)
        self.assertEqual(e_conv(b"3"), my_enum.quux)

    def test_enum_string(self):
        class my_enum(Enum):
            foo = "abc"
            bar = "def"
            quux = "xyz"

        def str_cast(value: bytes) -> str:
            return value.decode()

        e_conv = Convertor.enum_factory(my_enum, str_cast)
        self.assertEqual(e_conv(b"abc"), my_enum.foo)
        self.assertEqual(e_conv(b"def"), my_enum.bar)
        self.assertEqual(e_conv(b"xyz"), my_enum.quux)


if __name__ == "__main__":
    unittest.main()
