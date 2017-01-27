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
from types import IntType, FloatType, StringType

from irobot.common import type_check, type_check_collection


if __debug__:
    class TestTypeCheck(unittest.TestCase):
        def test_too_few_arguments(self):
            self.assertRaises(AssertionError, type_check, 1)
            self.assertRaises(AssertionError, type_check_collection, [1, 2, 3])

        def test_simple(self):
            self.assertIsNone(type_check(1, IntType))
            self.assertRaises(TypeError, type_check, 1, StringType)

        def test_union(self):
            self.assertIsNone(type_check(1, IntType, StringType))
            self.assertRaises(TypeError, type_check, 'foo', IntType, FloatType)

        def test_collection(self):
            self.assertIsNone(type_check_collection([1, 2, 3], IntType))
            self.assertIsNone(type_check_collection([1, 2.3, 4.56], IntType, FloatType))
            self.assertRaises(TypeError, type_check_collection, 1)
            self.assertRaises(TypeError, type_check_collection, [1, 2, 3], StringType)

else:
    class TestTypeCheck(unittest.TestCase):
        def test_passthrough(self):
            self.assertIsNone(type_check())
            self.assertIsNone(type_check_collection())


if __name__ == "__main__":
    unittest.main()
