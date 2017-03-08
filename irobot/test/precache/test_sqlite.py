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
from math import sqrt
from random import sample
from statistics import stdev

import irobot.precache._sqlite as _sqlite


class TestAdaptorsAndConvertors(unittest.TestCase):
    def test_adaptor_registration(self):
        def my_adaptor(x) -> str:
            return f"{x.real} + {x.imag}i"

        conn = _sqlite.Connection(":memory:")
        conn.register_adaptor(complex, my_adaptor)

        c = conn.cursor()
        adapted, = c.execute("select ?", (1 + 2j,)).fetchone()
        self.assertEqual(adapted, "1.0 + 2.0i")

        conn.close()

    def test_adapt_binding_dict(self):
        def my_adaptor(x) -> str:
            return f"COMPLEX {x}"

        conn = _sqlite.Connection(":memory:")
        conn.register_adaptor(complex, my_adaptor)

        c = conn.cursor()
        adapted, = c.execute("select :foo", {"foo": 1+2j}).fetchone()
        self.assertEqual(adapted, f"COMPLEX {1+2j}")

        conn.close()

    def test_bad_bindings(self):
        conn = _sqlite.Connection(":memory:")
        
        c = conn.cursor()
        self.assertRaises(TypeError, c.execute, "select ?", ["foo"])

        conn.close()

    def test_no_such_adaptor(self):
        conn = _sqlite.Connection(":memory:")

        c = conn.cursor()
        self.assertRaises(TypeError, c.execute, "select ?", (datetime.now(),))

        conn.close()

    def test_convertor_registration(self):
        def my_convertor(x) -> complex:
            return complex(x)
            
        conn = _sqlite.Connection(":memory:")
        conn.register_convertor("COMPLEX", my_convertor)

        c = conn.cursor()
        c.execute("create table foo(bar COMPLEX)")
        c.execute("insert into foo values (\"1+2j\")")

        converted, = c.execute("select bar from foo").fetchone()
        self.assertEqual(converted, 1 + 2j)

        conn.close()

    def test_datetime_adaptor(self):
        dt_adapt = _sqlite.datetime_adaptor
        self.assertEqual(dt_adapt(datetime(1970, 1, 1)), 0)
        self.assertEqual(dt_adapt(datetime(1970, 1, 2)), 86400)

    def test_datetime_convertor(self):
        dt_conv = _sqlite.datetime_convertor
        self.assertEqual(dt_conv(b"0"), datetime(1970, 1, 1))
        self.assertEqual(dt_conv(b"86400"), datetime(1970, 1, 2))

    def test_timedelta_adaptor(self):
        d_adapt = _sqlite.timedelta_adaptor
        self.assertEqual(d_adapt(timedelta(seconds=123)), 123.0)
        self.assertEqual(d_adapt(timedelta(days=1)), 86400.0)

    def test_timedelta_convertor(self):
        d_conv = _sqlite.timedelta_convertor
        self.assertEqual(d_conv(b"0"), timedelta(0))
        self.assertEqual(d_conv(b"1.23"), timedelta(seconds=1.23))
        self.assertEqual(d_conv(b"86400.0"), timedelta(days=1))

    def test_enum_adaptor(self):
        my_enum = Enum("my_enum", "foo bar quux")
        e_adapt = _sqlite.enum_adaptor
        self.assertEqual(e_adapt(my_enum.foo), 1)
        self.assertEqual(e_adapt(my_enum.bar), 2)
        self.assertEqual(e_adapt(my_enum.quux), 3)

    def test_enum_convertor_int(self):
        my_enum = Enum("my_enum", "foo bar quux")
        e_conv = _sqlite.enum_convertor_factory(my_enum)
        self.assertEqual(e_conv(b"1"), my_enum.foo)
        self.assertEqual(e_conv(b"2"), my_enum.bar)
        self.assertEqual(e_conv(b"3"), my_enum.quux)

    def test_enum_convertor_string(self):
        class my_enum(Enum):
            foo = "abc"
            bar = "def"
            quux = "xyz"

        def str_cast(value:bytes) -> str:
            return value.decode()

        e_conv = _sqlite.enum_convertor_factory(my_enum, str_cast)
        self.assertEqual(e_conv(b"abc"), my_enum.foo)
        self.assertEqual(e_conv(b"def"), my_enum.bar)
        self.assertEqual(e_conv(b"xyz"), my_enum.quux)


class TestUDFs(unittest.TestCase):
    def test_aggregate_registration(self):
        class MyCount(_sqlite.AggregateUDF):
            def __init__(self):
                self._count = 0

            @property
            def name(self):
                return "my_count"

            def step(self, *args):
                self._count += 1

            def finalise(self):
                return self._count

        conn = _sqlite.Connection(":memory:")
        conn.register_aggregate_function(MyCount)

        c = conn.cursor()
        c.execute("create table foo(bar)")
        c.executemany("insert into foo values (?)", list(map(lambda x: (x,), range(10))))

        my_count, = c.execute("select my_count(bar) from foo").fetchone()
        self.assertEqual(my_count, 10)

        conn.close()

    def test_bad_aggregate_function(self):
        class BadAggregate(_sqlite.AggregateUDF):
            @property
            def name(self):
                pass

            def step(self, **kwargs):
                pass

            def finalise(self):
                pass

        conn = _sqlite.Connection(":memory:")
        self.assertRaises(TypeError, conn.register_aggregate_function, BadAggregate)
        conn.close()

    def test_stderr(self):
        stderr = _sqlite.UDF.StandardError()

        self.assertEqual(stderr.name, "stderr")

        # Pass over non-numeric input
        stderr.step("foo")
        self.assertIsNone(stderr.finalise())

        data = []
        for i, x in enumerate(sample(range(100), 20)):
            stderr.step(x)
            data.append(x)

            if i == 0:
                # Need at least two numeric data points
                self.assertIsNone(stderr.finalise())

            if i > 0:
                calculated = stdev(data) / sqrt(i + 1)
                self.assertAlmostEqual(stderr.finalise(), calculated)


class TestCursor(unittest.TestCase):
    def setUp(self):
        self.conn = _sqlite.Connection(":memory:")

    def test_iterator(self):
        c = self.conn.cursor()
        c.execute("create table foo(bar)")
        c.executemany("insert into foo values (?)", list(map(lambda x: (x,), range(10))))

        summation = 0
        for row in c.execute("select * from foo"):
            summation += row[0]

        self.assertEqual(summation, 45)

    def test_fetchall(self):
        data = list(map(lambda x: (x,), range(10)))

        c = self.conn.cursor()
        c.execute("create table foo(bar)")
        c.executemany("insert into foo values (?)", data)

        self.assertEqual(c.execute("select * from foo order by bar").fetchall(), data)

    def test_empty_fetchone(self):
        c = self.conn.cursor()
        self.assertIsNone(c.fetchone())

    def tearDown(self):
        self.conn.close()

if __name__ == "__main__":
    unittest.main()
