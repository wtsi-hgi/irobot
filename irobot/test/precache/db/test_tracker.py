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

import math
import os
import random
import statistics
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from tempfile import NamedTemporaryFile

import irobot.precache.db.tracker as _tracker
from irobot.common import AsyncTaskStatus, DataObjectState
from irobot.precache.db import TrackingDB
from irobot.precache.db._exceptions import PrecacheExists, StatusExists


class TestMisc(unittest.TestCase):
    def test_nuple(self):
        self.assertEqual(_tracker._nuple(),  (None,))
        self.assertEqual(_tracker._nuple(2), (None, None))
        self.assertEqual(_tracker._nuple(3), (None, None, None))


class TestDBMagic(unittest.TestCase):
    """
    Specifically test the automatic features of the database's schema,
    such as triggers and cascades, by checking state and changes thereof
    """
    def setUp(self):
        self.tracker = TrackingDB(":memory:")

        # Create a dummy record
        self.tracker._exec("insert into data_objects(irods_path, precache_path) values (\"foo\", \"bar\")")
        self.do_id, = self.tracker._exec("select id from data_objects where irods_path = ?", ("foo",)).fetchone() or (None,)

    def test_auto_first_status_trigger(self):
        for datatype in DataObjectState:
            status, = self.tracker._exec("select status from status_log where data_object = ? and datatype = ?", (self.do_id, datatype)).fetchone() or (None,)
            self.assertEqual(status, AsyncTaskStatus.queued)

    def test_cascade_delete_data_object(self):
        for datatype, size in (DataObjectState.data, 123), (DataObjectState.metadata, 456), (DataObjectState.checksums, 789):
            self.tracker._exec("""
                insert into data_sizes (data_object, datatype, size)
                                values (?, ?, ?);
            """, (self.do_id, datatype, size))

        self.tracker._exec("delete from data_objects where id = ?", (self.do_id,))

        sizes, = self.tracker._exec("select count(*) from data_sizes where data_object = ?", (self.do_id,)).fetchone()
        statuses, = self.tracker._exec("select count(*) from status_log where data_object = ?", (self.do_id,)).fetchone()
        self.assertEqual(sizes, 0)
        self.assertEqual(statuses, 0)

    def test_reset_bad_state_on_init(self):
        with NamedTemporaryFile() as temp_db:
            before = TrackingDB(temp_db.name)
            (before_count,), *_ = before._exec("""
                begin immediate transaction;

                insert into data_objects (irods_path, precache_path)
                                  values ("foo", "bar");

                insert into status_log (data_object, datatype, status)
                    select     data_objects.id,
                               datatypes.id,
                               2
                    from       data_objects
                    cross join datatypes
                    where      data_objects.irods_path = "foo";

                select count(*)
                from   current_status
                where  status = 2;

                commit;
            """).fetchall()
            self.assertEqual(before_count, len(DataObjectState))

            before.conn.close()
            del before

            after = TrackingDB(temp_db.name)
            after_count, = after._exec("select count(*) from current_status where status = 2").fetchone()
            self.assertEqual(after_count, 0)

            sanity_check, = after._exec("select count(*) from current_status where status = 1").fetchone()
            self.assertEqual(sanity_check, len(DataObjectState))


class TestTrackingDB(unittest.TestCase):
    def setUp(self):
        self.tracker = TrackingDB(":memory:")
        self.mock_connection = MagicMock(spec=_tracker.Connection)

    @patch("irobot.precache.db.tracker.Timer", spec=True)
    def test_cleanup_on_gc(self, mock_timer):
        tracker = TrackingDB(":memory:")
        tracker.conn = self.mock_connection
        mock_timer.is_alive.return_value = True

        tracker.__del__()
        tracker._vacuum_timer.is_alive.assert_called_once()
        tracker._vacuum_timer.cancel.assert_called_once()
        tracker.conn.close.assert_called_once()

    def test_vacuum(self):
        self.tracker.conn = self.mock_connection
        self.tracker._vacuum()
        self.tracker.conn.cursor().execute.assert_called_once_with("vacuum")

    def test_external_commitment(self):
        self.assertEqual(self.tracker.commitment, 0)
        self.tracker.new_request("foo", "bar", (123, 456, 789))
        self.assertEqual(self.tracker.commitment, 1368)

    def test_internal_commitment(self):
        with NamedTemporaryFile() as temp_db:
            db_file= temp_db.name
            tracker = TrackingDB(db_file, True)
            self.assertEqual(tracker.commitment, os.stat(db_file).st_size)

    def test_production_rates(self):
        self.assertEqual(self.tracker.production_rates, {DataObjectState.data: None, DataObjectState.checksums: None})

        data_size      = random.randint(500, 2000)
        start_time     = random.randint(0, 3600)
        download_times = [t + start_time + 1 for t in random.sample(range(100), 3)]
        checksum_times = [t + start_time + 1 for t in random.sample(range(100), 3)]

        # Set initial state
        self.tracker._exec("""
            begin immediate transaction;

            insert into data_objects (id, irods_path, precache_path)
                              values (1,  "foo",      "foo"),
                                     (2,  "bar",      "bar"),
                                     (3,  "quux",     "quux");

            insert into data_sizes (data_object, datatype, size)
                select id, 1, ?
                from   data_objects;

            update status_log set timestamp = 0;

            -- Set the producing time
            insert into status_log (timestamp, data_object, datatype, status)
                select     ?, data_objects.id, datatypes.id, 2
                from       data_objects
                cross join datatypes;

            commit;
        """, (data_size, start_time))

        # Set ready times
        self.tracker.conn.cursor().executemany("""
            insert into status_log (timestamp, data_object, datatype, status)
                        values     (?,         ?,          ?,        ?)
        """, [
            (timestamp, data_object, DataObjectState.data, AsyncTaskStatus.finished)
            for data_object, timestamp
            in  enumerate(download_times, 1)
        ] + [
            (timestamp, data_object, DataObjectState.checksums, AsyncTaskStatus.finished)
            for data_object, timestamp
            in  enumerate(checksum_times, 1)
        ])

        for stat, times in (DataObjectState.data, download_times), (DataObjectState.checksums, checksum_times):
            rates = [data_size / (t - start_time) for t in times]

            self.assertAlmostEqual(
                self.tracker.production_rates[stat].mean,
                statistics.mean(rates)
            )

            self.assertAlmostEqual(
                self.tracker.production_rates[stat].stderr,
                statistics.stdev(rates) / math.sqrt(len(times))
            )

    def test_state(self):
        do_ids = []
        for i in range(10):
            do_ids.append(self.tracker.new_request(f"foo{i}", f"bar{i}", (0, 0, 0)))

        self.assertCountEqual(self.tracker.precache_entities, do_ids)

    def test_get_do_id(self):
        do_id = self.tracker.new_request("foo", "bar", (0, 0, 0))
        self.assertEqual(self.tracker.get_data_object_id("foo"), do_id)
        self.assertIsNone(self.tracker.get_data_object_id("quux"))

    def test_get_precache_path(self):
        do_id = self.tracker.new_request("foo", "bar", (0, 0, 0))
        self.assertEqual(self.tracker.get_precache_path(do_id), "bar")

    def test_last_access(self):
        self.assertIsNone(self.tracker.get_last_access(1))

        do_id = self.tracker.new_request("foo", "bar", (0, 0, 0))
        last_access, = self.tracker._exec("select last_access from data_objects where id = ?", (do_id,)).fetchone()
        self.assertEqual(self.tracker.get_last_access(do_id), last_access)

    def test_update_last_access(self):
        start = datetime.utcnow()

        do_id = self.tracker.new_request("foo", "bar", (0, 0, 0))
        first_access = self.tracker.get_last_access(do_id)

        self.tracker.update_last_access(do_id)
        last_access = self.tracker.get_last_access(do_id)

        op_duration = datetime.utcnow() - start
        self.assertLessEqual(last_access - first_access, op_duration)

    def test_status(self):
       self.assertIsNone(self.tracker.get_current_status(123, DataObjectState.data))

       do_id = self.tracker.new_request("foo", "bar", (0, 0, 0))
       self.assertEqual(self.tracker.get_current_status(do_id, DataObjectState.data).status, AsyncTaskStatus.queued)

       self.tracker.set_status(do_id, DataObjectState.data, AsyncTaskStatus.started)
       self.assertEqual(self.tracker.get_current_status(do_id, DataObjectState.data).status, AsyncTaskStatus.started)

       self.assertRaises(StatusExists, self.tracker.set_status, do_id, DataObjectState.data, AsyncTaskStatus.started)

    def test_size(self):
        self.assertIsNone(self.tracker.get_size(123, DataObjectState.data))

        do_id = self.tracker.new_request("foo", "bar", (123, 456, 789))
        self.assertEqual(self.tracker.get_size(do_id, DataObjectState.data), 123)
        self.assertEqual(self.tracker.get_size(do_id, DataObjectState.metadata), 456)
        self.assertEqual(self.tracker.get_size(do_id, DataObjectState.checksums), 789)

    def test_new_request(self):
        do_id = self.tracker.new_request("foo", "bar", (123, 456, 789))

        self.assertRaises(PrecacheExists, self.tracker.new_request, "foo", "quux", (123, 456, 789))
        self.assertRaises(PrecacheExists, self.tracker.new_request, "quux", "bar", (123, 456, 789))

    def test_delete_object(self):
        do_id = self.tracker.new_request("foo", "bar", (123, 456, 789))
        self.tracker.delete_data_object(do_id)

        records, = self.tracker._exec("""
            with _counts as (
                select count(*) as c from data_objects
                union all
                select count(*) as c from data_sizes
                union all
                select count(*) as c from status_log
            )
            select sum(c) from _counts;
        """).fetchone()

        self.assertEqual(records, 0)


if __name__ == "__main__":
    unittest.main()
