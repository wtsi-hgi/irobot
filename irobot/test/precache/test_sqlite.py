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
from unittest.mock import MagicMock
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Tuple

import irobot.precache._sqlite as _sqlite


class TestMentalSQLRegEx(unittest.TestCase):
    def _assert_writes(self, *statements:Tuple[str, ...]):
        for statement in statements:
            self.assertIsNotNone(_sqlite._potentially_writes(statement))

    def _assert_no_write(self, *statements:Tuple[str, ...]):
        for statement in statements:
            self.assertIsNone(_sqlite._potentially_writes(statement))

    def test_select(self):
        self._assert_no_write(
            "select * from foo",
            "with foo as (select * from bar) select * from foo",
            "explain query plan select * from foo"
        )

    def test_transaction_block(self):
        self._assert_writes(
            "begin",
            "begin transaction",
            "begin deferred",
            "begin deferred transaction",
            "begin immediate",
            "begin immediate transaction",
            "begin exclusive",
            "begin exclusive transaction",

            "commit",
            "commit transaction",
            "end",
            "end transaction",

            "rollback",
            "rollback transaction to savepoint foo"
        )

    def test_misc(self):
        self._assert_writes(
            "pragma foo.bar(123)",
            "analyze",
            "vacuum",
            "savepoint foo",
            "release foo",
            "release savepoint foo"
        )

    def test_table(self):
        self._assert_writes(
            "create table foo.bar (quux)",
            "alter table foo.bar add column quux",
            "alter table foo.bar rename",
            "create temp table foo",
            "create temporary table foo",
            "create table if not exists foo",
            "create virtual table foo using bar",
            "create virtual table if not exists foo using bar",
            "drop table foo",
            "drop table if exists foo.bar"
        )

    def test_index(self):
        self._assert_writes(
            "create index foo.bar on quux",
            "create unique index foo on bar",
            "create index if not exists foo on quux",
            "reindex",
            "drop index foo",
            "drop index if exists foo.bar"
        )

    def test_view(self):
        self._assert_writes(
            "create view foo",
            "create view if not exists foo.bar",
            "create temp view foo",
            "create temporary view foo.bar",
            "drop view foo",
            "drop view if exists foo.bar"
        )

    def test_trigger(self):
        self._assert_writes(
            "create trigger foo",
            "create trigger if not exists foo.bar",
            "create temp trigger foo",
            "create temporary trigger foo.bar",
            "drop trigger foo",
            "drop trigger if exists foo.bar"
        )

    def test_dml(self):
        self._assert_writes(
            "insert into foo",
            "insert into foo.bar",
            "replace into foo",
            "insert or replace into foo",
            "insert or rollback into foo",
            "insert or abort into foo",
            "insert or fail into foo",
            "insert or ignore into foo",

            "update foo set",
            "update or rollback foo.bar set",
            "update or abort foo set",
            "update or replace foo set",
            "update or fail foo set",
            "update or ignore foo set",

            "delete from foo",
            "delete from foo.bar"
        )


class TestUDFs(unittest.TestCase):
    def test_stderr(self):
        stderr = _sqlite.StandardErrorUDF()
        for x in ["foo"] + list(range(10)):
            stderr.step(x)

            # Need at least two numeric data points
            if x in ["foo", 0]:
                self.assertIsNone(stderr.finalize())

        self.assertAlmostEqual(stderr.finalize(), 0.957427107756338)


class TestThreadSafeConnection(unittest.TestCase):
    def setUp(self):
        self._old_lock, _sqlite.Lock = _sqlite.Lock, MagicMock(spec=Lock)
        self.connection = _sqlite.connect(":memory:")

    def tearDown(self):
        self.connection.close()
        _sqlite.Lock = self._old_lock

    def test_connection(self):
        self.assertFalse(self.connection.in_transaction)
        self.assertEqual(self.connection.total_changes, 0)

    def test_commit(self):
        self.connection.commit()
        self.connection._write_lock.acquire.assert_called_once()
        self.connection._write_lock.release.assert_called_once()
    
    def test_execute(self):
        cur = self.connection.execute("select 123")
        self.assertEqual(cur.fetchone(), (123,))
        self.connection._write_lock.acquire.assert_not_called()

        self.connection.execute("create table foo(bar)")
        self.connection._write_lock.acquire.assert_called_once()
        self.connection._write_lock.release.assert_called_once()

    def test_executemany(self):
        self.connection.execute("create table foo(bar)")
        self.connection._write_lock.reset_mock()

        self.connection.executemany("insert into foo(bar) values (?)", [(1,), (2,), (3,)])
        self.connection._write_lock.acquire.assert_called_once()
        self.connection._write_lock.release.assert_called_once()

    def test_executescript(self):
        self.connection.executescript("select 123; select 456;")
        self.connection._write_lock.acquire.assert_not_called()
        
        self.connection.executescript("create table foo(bar); select * from foo;")
        self.connection._write_lock.acquire.assert_called_once()
        self.connection._write_lock.release.assert_called_once()

    def test_context_manager(self):
        conn = _sqlite.connect(":memory:", isolation_level=_sqlite.IsolationLevel.DEFERRED)

        with conn:
            conn.execute("create table foo(bar)")
            conn.execute("insert into foo(bar) values (123)")

        conn._write_lock.acquire.assert_called_once()
        conn._write_lock.release.assert_called_once()


class TestThreadSafeWriting(unittest.TestCase):
    def test_multithread_write(self):
        conn = _sqlite.connect(":memory:")
        conn.execute("create table foo(bar)")

        with ThreadPoolExecutor() as executor:
            for x in range(10):
                executor.submit(conn.execute, "insert into foo(bar) values (?)", (x,))

        conn.row_factory = lambda _, row: row[0]
        self.assertEqual(conn.execute("select bar from foo order by bar").fetchall(), list(range(10)))

        conn.close()


if __name__ == "__main__":
    unittest.main()
