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

import irobot.precache.db._dbi as _dbi
from irobot.precache.db._udf import AggregateUDF


class TestCursor(unittest.TestCase):
    def setUp(self):
        self.conn = _dbi.Connection(":memory:")

    def tearDown(self):
        self.conn.close()

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

    def test_aggregate_registration(self):
        class MyCount(AggregateUDF):
            def __init__(self):
                self._count = 0

            def step(self, *args):
                self._count += 1

            def finalise(self):
                return self._count

        self.conn.register_aggregate_function("my_count", MyCount)

        c = self.conn.cursor()
        c.execute("create table foo(bar)")
        c.executemany("insert into foo values (?)", list(map(lambda x: (x,), range(10))))

        my_count, = c.execute("select my_count(bar) from foo").fetchone()
        self.assertEqual(my_count, 10)

    def test_bad_aggregate_function(self):
        class BadAggregate(_dbi.AggregateUDF):
            def step(self, **kwargs):
                pass

            def finalise(self):
                pass

        self.assertRaises(TypeError, self.conn.register_aggregate_function, "foo", BadAggregate)

    def test_adaptor_registration(self):
        def my_adaptor(x) -> str:
            return f"{x.real} + {x.imag}i"

        self.conn.register_adaptor(complex, my_adaptor)

        c = self.conn.cursor()
        adapted, = c.execute("select ?", (1 + 2j,)).fetchone()
        self.assertEqual(adapted, "1.0 + 2.0i")

    def test_adapt_binding_dict(self):
        def my_adaptor(x) -> str:
            return f"COMPLEX {x}"

        self.conn.register_adaptor(complex, my_adaptor)

        c = self.conn.cursor()
        adapted, = c.execute("select :foo", {"foo": 1 + 2j}).fetchone()
        self.assertEqual(adapted, f"COMPLEX {1+2j}")

    def test_bad_bindings(self):
        c = self.conn.cursor()
        self.assertRaises(TypeError, c.execute, "select ?", ["foo"])

    def test_no_such_adaptor(self):
        c = self.conn.cursor()
        self.assertRaises(TypeError, c.execute, "select ?", (1 + 2j,))

    def test_convertor_registration(self):
        def my_convertor(x) -> complex:
            return complex(x)

        self.conn.register_convertor("COMPLEX", my_convertor)

        c = self.conn.cursor()
        c.execute("create table foo(bar COMPLEX)")
        c.execute("insert into foo values (\"1+2j\")")

        converted, = c.execute("select bar from foo").fetchone()
        self.assertEqual(converted, 1 + 2j)


if __name__ == "__main__":
    unittest.main()
