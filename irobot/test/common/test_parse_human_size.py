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

from irobot.common import parse_human_size


class TestParseHumanSize(unittest.TestCase):
    def test_bytes(self):
        self.assertRaises(ValueError, parse_human_size, "foo")
        self.assertRaises(ValueError, parse_human_size, "1.2B")
        self.assertRaises(ValueError, parse_human_size, "1.2 B")

        self.assertEquals(parse_human_size("1"),        1)
        self.assertEquals(parse_human_size("12"),       12)
        self.assertEquals(parse_human_size("123"),      123)
        self.assertEquals(parse_human_size("1234B"),    1234)
        self.assertEquals(parse_human_size("12345 B"),  12345)

    def test_decimal_multiplier(self):
        self.assertRaises(ValueError, parse_human_size, "1 KB")
        self.assertRaises(ValueError, parse_human_size, "1 XB")

        self.assertEquals(parse_human_size("1kB"),      1000)
        self.assertEquals(parse_human_size("1.2kB"),    1.2 * 1000)
        self.assertEquals(parse_human_size("1.23 kB"),  1.23 * 1000)
        self.assertEquals(parse_human_size("1MB"),      1000**2)
        self.assertEquals(parse_human_size("1.2MB"),    1.2 * (1000**2))
        self.assertEquals(parse_human_size("1.23 MB"),  1.23 * (1000**2))
        self.assertEquals(parse_human_size("1GB"),      1000**3)
        self.assertEquals(parse_human_size("1.2GB"),    1.2 * (1000**3))
        self.assertEquals(parse_human_size("1.23 GB"),  1.23 * (1000**3))
        self.assertEquals(parse_human_size("1TB"),      1000**4)
        self.assertEquals(parse_human_size("1.2TB"),    1.2 * (1000**4))
        self.assertEquals(parse_human_size("1.23 TB"),  1.23 * (1000**4))

    def test_binary_multiplier(self):
        self.assertRaises(ValueError, parse_human_size, "1 KiB")
        self.assertRaises(ValueError, parse_human_size, "1 kIB")
        self.assertRaises(ValueError, parse_human_size, "1 XiB")

        self.assertEquals(parse_human_size("1kiB"),     1024)
        self.assertEquals(parse_human_size("1.2kiB"),   1.2 * 1024)
        self.assertEquals(parse_human_size("1.23 kiB"), 1.23 * 1024)
        self.assertEquals(parse_human_size("1MiB"),     1024**2)
        self.assertEquals(parse_human_size("1.2MiB"),   1.2 * (1024**2))
        self.assertEquals(parse_human_size("1.23 MiB"), 1.23 * (1024**2))
        self.assertEquals(parse_human_size("1GiB"),     1024**3)
        self.assertEquals(parse_human_size("1.2GiB"),   1.2 * (1024**3))
        self.assertEquals(parse_human_size("1.23 GiB"), 1.23 * (1024**3))
        self.assertEquals(parse_human_size("1TiB"),     1024**4)
        self.assertEquals(parse_human_size("1.2TiB"),   1.2 * (1024**4))
        self.assertEquals(parse_human_size("1.23 TiB"), 1.23 * (1024**4))


if __name__ == "__main__":
    unittest.main()
