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
from types import FloatType, IntType, StringType

from irobot.common import type_check, type_check_collection, type_check_arguments, type_check_return


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
            self.assertRaises(TypeError, type_check, "foo", IntType, FloatType)

        def test_collection(self):
            self.assertIsNone(type_check_collection([1, 2, 3], IntType))
            self.assertIsNone(type_check_collection([1, 2.3, 4.56], IntType, FloatType))
            self.assertRaises(TypeError, type_check_collection, 1)
            self.assertRaises(TypeError, type_check_collection, [1, 2, 3], StringType)

        def test_collection_mapping(self):
            self.assertIsNone(type_check_collection({"foo": 1, "bar": 2}, IntType))
            self.assertIsNone(type_check_collection({"foo": 1, "bar": 2.3}, IntType, FloatType))
            self.assertRaises(TypeError, type_check_collection, {"foo": 1, "bar": "quux"}, IntType)

        def test_return(self):
            @type_check_return()
            def _return_none_pass():
                pass

            @type_check_return()
            def _return_none_fail():
                return 123

            self.assertIsNone(_return_none_pass())
            self.assertRaises(TypeError, _return_none_fail)

            @type_check_return(IntType)
            def _return_int_pass():
                return 123

            @type_check_return(IntType)
            def _return_int_fail():
                return "foo"

            self.assertEqual(_return_int_pass(), 123)
            self.assertRaises(TypeError, _return_int_fail)

            @type_check_return(StringType)
            def _return_collection_pass():
                return ["a", "b", "c"]

            @type_check_return(StringType)
            def _return_collection_fail():
                return ["a", "b", "c", 1, 2, 3]

            self.assertEqual(_return_collection_pass(), ["a", "b", "c"])
            self.assertRaises(TypeError, _return_collection_fail)

        def test_arguments(self):
            @type_check_arguments()
            def _no_check(a, b=123, *c, **d):
                pass

            self.assertIsNone(_no_check("foo", "bar", 123, 456, quux="xyzzy"))

            @type_check_arguments(a=IntType)
            def _simple(a):
                pass

            self.assertRaises(TypeError, _simple, "foo")
            self.assertIsNone(_simple(123))

            @type_check_arguments(a=(IntType, StringType))
            def _simple_union(a):
                pass

            self.assertRaises(TypeError, _simple_union, 1.1)
            self.assertIsNone(_simple_union(123))
            self.assertIsNone(_simple_union("foo"))

            @type_check_arguments(a=IntType, b=StringType)
            def _default(a, b="foo"):
                pass

            self.assertRaises(TypeError, _default, 123, 456)
            self.assertIsNone(_default(123))
            self.assertIsNone(_default(123, "bar"))

            @type_check_arguments(args=StringType)
            def _varargs(*args):
                pass

            self.assertRaises(TypeError, _varargs, 1, 2, 3)
            self.assertRaises(TypeError, _varargs, 1, "foo", 3)
            self.assertIsNone(_varargs("foo", "bar", "baz"))

            @type_check_arguments(kwargs=IntType)
            def _kwargs(**kwargs):
                pass

            self.assertRaises(TypeError, _kwargs, foo="bar")
            self.assertRaises(TypeError, _kwargs, foo=1, bar="quux")
            self.assertIsNone(_kwargs(foo=1, bar=2))


if __name__ == "__main__":
    unittest.main()
