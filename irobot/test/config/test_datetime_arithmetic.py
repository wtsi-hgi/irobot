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

from irobot.config._datetime_arithmetic import multiply_timedelta, add_years


class TestDateTimeArithmetic(unittest.TestCase):
    def setUp(self):
        # n.b., 2000 was a leap year
        self.base = datetime(2000, 1, 1)

    def test_type_assertions(self):
        self.assertRaises(TypeError, multiply_timedelta, 0, 0)
        self.assertRaises(TypeError, multiply_timedelta, timedelta(), 'foo')
        self.assertRaises(TypeError, add_years, 0, 0)
        self.assertRaises(TypeError, add_years, datetime.utcnow(), 'foo')

    def test_whole_year_shift(self):
        self.assertEqual(add_years(self.base,  0), self.base)
        self.assertEqual(add_years(self.base,  1), datetime(2001, 1, 1))
        self.assertEqual(add_years(self.base,  2), datetime(2002, 1, 1))
        self.assertEqual(add_years(self.base,  3), datetime(2003, 1, 1))
        self.assertEqual(add_years(self.base,  4), datetime(2004, 1, 1))
        self.assertEqual(add_years(self.base,  5), datetime(2005, 1, 1))
        self.assertEqual(add_years(self.base, -1), datetime(1999, 1, 1))
        self.assertEqual(add_years(self.base, -2), datetime(1998, 1, 1))
        self.assertEqual(add_years(self.base, -3), datetime(1997, 1, 1))
        self.assertEqual(add_years(self.base, -4), datetime(1996, 1, 1))
        self.assertEqual(add_years(self.base, -5), datetime(1995, 1, 1))

    def test_fractional_year_shift(self):
        self.assertEqual(add_years(self.base,  0.5), self.base + timedelta(366 / 2))
        self.assertEqual(add_years(self.base,  1.5), self.base + timedelta(366 + (365 / 2.0)))
        self.assertEqual(add_years(self.base, -0.5), self.base - timedelta(365 / 2.0))
        self.assertEqual(add_years(self.base, -1.5), self.base - timedelta(365 + (365 / 2.0)))


if __name__ == "__main__":
    unittest.main()
