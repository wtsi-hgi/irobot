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
from irobot.precache.db import TrackingDB, Datatype, Mode, Status
from irobot.precache.db._exceptions import PrecacheExists, StatusExists, SwitchoverExists, SwitchoverDoesNotExist


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

        # Create a dummy record; this belongs to the auto_request
        # trigger test, but it's also common to everything else
        self.tracker._exec("insert into do_requests(irods_path, precache_path) values (\"foo\", \"bar\")")
        self.do_id, = self.tracker._exec("select id from data_objects where irods_path = ?", ("foo",)).fetchone() or (None,)

    def test_auto_request_trigger(self):
        self.assertIsNotNone(self.do_id)

        precache_path, = self.tracker._exec("select precache_path from do_modes where data_object = ? and mode = 1", (self.do_id,)).fetchone() or (None,)
        self.assertEqual(precache_path, "bar")

    def test_auto_first_access_trigger(self):
        last_access_sql = "select last_access from last_access where data_object = ?"

        first_access, = self.tracker._exec(last_access_sql, (self.do_id,)).fetchone() or (None,)
        self.assertIsNotNone(first_access)

        self.tracker._exec("insert into do_modes(data_object, mode, precache_path) values (?, 2, \"quux\")", (self.do_id,))

        no_change, = self.tracker._exec(last_access_sql, (self.do_id,)).fetchone() or (None,)
        self.assertEqual(first_access, no_change)

    def test_auto_first_status_trigger(self):
        dom_id, = self.tracker._exec("select id from do_modes where data_object = ? and mode = 1", (self.do_id,)).fetchone()

        for datatype in Datatype:
            status, = self.tracker._exec("select status from status_log where dom_file = ? and datatype = ?", (dom_id, datatype)).fetchone() or (None,)
            self.assertEqual(status, Status.requested)

    def test_cascade_delete_data_object(self):
        self.tracker._exec("insert into do_modes(data_object, mode, precache_path) values (?, 2, \"quux\")", (self.do_id,))

        doms, = self.tracker._exec("select count(*) from do_modes where data_object = ?", (self.do_id,)).fetchone()
        self.assertEqual(doms, 2)

        last_access, = self.tracker._exec("select last_access from last_access where data_object = ?", (self.do_id,)).fetchone() or (None,)
        self.assertIsNotNone(last_access)

        self.tracker._exec("delete from data_objects where id = ?", (self.do_id,))

        doms, = self.tracker._exec("select count(*) from do_modes where data_object = ?", (self.do_id,)).fetchone()
        self.assertEqual(doms, 0)

        last_access, = self.tracker._exec("select last_access from last_access where data_object = ?", (self.do_id,)).fetchone() or (None,)
        self.assertIsNone(last_access)

    def test_cascade_delete_data_object_mode(self):
        dom_id, = self.tracker._exec("select id from do_modes where data_object = ? and mode = 1", (self.do_id,)).fetchone()

        self.tracker._exec("insert into data_sizes(dom_file, datatype, size) values (?, 1, 123)", (dom_id,))

        ds_count, = self.tracker._exec("select count(*) from data_sizes where dom_file = ?", (dom_id,)).fetchone()
        self.assertEqual(ds_count, 1)

        stat_count, = self.tracker._exec("select count(*) from status_log where dom_file = ?", (dom_id,)).fetchone()
        self.assertEqual(stat_count, len(Datatype))

        self.tracker._exec("delete from do_modes where id = ?", (dom_id,))

        ds_count, = self.tracker._exec("select count(*) from data_sizes where dom_file = ?", (dom_id,)).fetchone()
        self.assertEqual(ds_count, 0)

        stat_count, = self.tracker._exec("select count(*) from status_log where dom_file = ?", (dom_id,)).fetchone()
        self.assertEqual(stat_count, 0)

    def test_reset_bad_state_on_init(self):
        with NamedTemporaryFile() as temp_db:
            before = TrackingDB(temp_db.name)
            (before_count,), *_ = before._exec("""
                begin immediate transaction;

                insert into do_requests (irods_path, precache_path)
                                 values ("foo", "bar");

                insert into status_log (dom_file, datatype, status)
                    select     do_modes.id,
                               datatypes.id,
                               2
                    from       data_objects
                    join       do_modes
                    on         do_modes.data_object    = data_objects.id
                    and        do_modes.mode           = 1
                    cross join datatypes
                    where      data_objects.irods_path = "foo";

                select count(*)
                from   current_status
                where  status = 2;

                commit;
            """).fetchall()
            self.assertEqual(before_count, len(Datatype))

            before.conn.close()
            del before

            after = TrackingDB(temp_db.name)
            after_count, = after._exec("select count(*) from current_status where status = 2").fetchone()
            self.assertEqual(after_count, 0)

            sanity_check, = after._exec("select count(*) from current_status where status = 1").fetchone()
            self.assertEqual(sanity_check, len(Datatype))


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
        self.assertEqual(self.tracker.production_rates, {Datatype.data: None, Datatype.checksums: None})

        data_size      = random.randint(500, 2000)
        start_time     = random.randint(0, 3600)
        download_times = [t + start_time + 1 for t in random.sample(range(100), 3)]
        checksum_times = [t + start_time + 1 for t in random.sample(range(100), 4)]

        # Set initial state
        self.tracker._exec("""
            begin immediate transaction;

            insert into data_objects (id, irods_path)
                              values (1,  "foo"),
                                     (2,  "bar"),
                                     (3,  "quux");

            insert into do_modes (id, data_object, mode, precache_path)
                          values (1,  1,           1,    "foo"),
                                 (2,  2,           1,    "bar"),
                                 (3,  3,           1,    "quux"),
                                 (4,  3,           2,    "baz");

            insert into data_sizes (dom_file, datatype, size)
                select do_modes.id, 1, ?
                from   do_modes;

            update status_log set timestamp = 0;

            -- Set the producing time
            insert into status_log (timestamp, dom_file, datatype, status)
                select     ?, do_modes.id, datatypes.id, 2
                from       do_modes
                cross join datatypes;

            commit;
        """, (data_size, start_time))

        # Set ready times
        self.tracker.conn.cursor().executemany("""
            insert into status_log (timestamp, dom_file, datatype, status)
                        values     (?,         ?,        ?,        ?)
        """, [
            (timestamp, dom_file, Datatype.data, Status.ready)
            for dom_file, timestamp
            in  enumerate(download_times, 1)
        ] + [
            (timestamp, dom_file, Datatype.checksums, Status.ready)
            for dom_file, timestamp
            in  enumerate(checksum_times, 1)
        ])

        for stat, times in (Datatype.data, download_times), (Datatype.checksums, checksum_times):
            rates = [data_size / (t - start_time) for t in times]

            self.assertAlmostEqual(
                self.tracker.production_rates[stat].mean,
                statistics.mean(rates)
            )

            self.assertAlmostEqual(
                self.tracker.production_rates[stat].stderr,
                statistics.stdev(rates) / math.sqrt(len(times))
            )

    def test_get_do_id(self):
        do_id, _mode = self.tracker.new_request("foo", "bar", (0, 0, 0))
        self.assertEqual(self.tracker.get_data_object_id("foo"), do_id)
        self.assertIsNone(self.tracker.get_data_object_id("quux"))

    def test_get_precache_path(self):
        do_id, mode = self.tracker.new_request("foo", "bar", (0, 0, 0))
        self.assertEqual(self.tracker.get_precache_path(do_id, mode), "bar")

    def test_has_switchover(self):
        do_id1, mode1 = self.tracker.new_request("foo", "bar", (0, 0, 0))
        self.assertEqual(mode1, Mode.master)
        self.assertFalse(self.tracker.has_switchover(do_id1))

        do_id2, mode2 = self.tracker.new_request("foo", "quux", (0, 0, 0))
        self.assertEqual(do_id1, do_id2)
        self.assertEqual(mode2, Mode.switchover)
        self.assertTrue(self.tracker.has_switchover(do_id1))

    def test_last_access(self):
        self.assertEqual(self.tracker.get_last_access(), [])

        do_id, mode = self.tracker.new_request("foo", "bar", (0, 0, 0))
        last_access, = self.tracker._exec("select last_access from last_access where data_object = ?", (do_id,)).fetchone()
        self.assertEqual(self.tracker.get_last_access(), [(do_id, last_access)])
        self.assertEqual(self.tracker.get_last_access(do_id), [(do_id, last_access)])
        self.assertEqual(self.tracker.get_last_access(do_id + 123), [])

        with patch("irobot.precache.db.tracker.datetime") as mock_datetime:
            delta = timedelta(seconds=10)
            mock_datetime.utcnow.return_value = last_access + delta
            self.assertEqual(self.tracker.get_last_access(do_id, delta), [(do_id, last_access)])
            self.assertEqual(self.tracker.get_last_access(do_id, timedelta(seconds=11)), [])

        do_id2, _mode = self.tracker.new_request("quux", "xyzzy", (0, 0, 0))
        self.tracker._exec("update last_access set last_access = ? - 123 where data_object = ?", (last_access, do_id2))
        self.assertEqual(len(self.tracker.get_last_access()), 2)
        self.assertEqual(self.tracker.get_last_access()[0][0], do_id2)
        self.assertEqual(self.tracker.get_last_access()[1][0], do_id)

    def test_update_last_access(self):
        start = datetime.utcnow()

        do_id, _mode = self.tracker.new_request("foo", "bar", (0, 0, 0))
        [(_, first_access)] = self.tracker.get_last_access(do_id)

        self.tracker.update_last_access(do_id)
        [(_, last_access)] = self.tracker.get_last_access(do_id)

        op_duration = datetime.utcnow() - start
        self.assertLessEqual(last_access - first_access, op_duration)

    def test_status(self):
       self.assertIsNone(self.tracker.get_current_status(123, Mode.master, Datatype.data))

       do_id, mode = self.tracker.new_request("foo", "bar", (0, 0, 0))
       self.assertEqual(self.tracker.get_current_status(do_id, mode, Datatype.data).status, Status.requested)

       self.tracker.set_status(do_id, mode, Datatype.data, Status.producing)
       self.assertEqual(self.tracker.get_current_status(do_id, mode, Datatype.data).status, Status.producing)

       self.assertRaises(StatusExists, self.tracker.set_status, do_id, mode, Datatype.data, Status.producing)

    def test_size(self):
        self.assertIsNone(self.tracker.get_size(123, Mode.master, Datatype.data))

        do_id, mode = self.tracker.new_request("foo", "bar", (123, 456, 789))
        self.assertEqual(self.tracker.get_size(do_id, mode, Datatype.data), 123)
        self.assertEqual(self.tracker.get_size(do_id, mode, Datatype.metadata), 456)
        self.assertEqual(self.tracker.get_size(do_id, mode, Datatype.checksums), 789)

    def test_new_request(self):
        do_id, mode = self.tracker.new_request("foo", "bar", (123, 456, 789))
        self.assertEqual(mode, Mode.master)

        self.assertRaises(PrecacheExists, self.tracker.new_request, "foo", "bar", (123, 456, 789))

        do_id2, mode2 = self.tracker.new_request("foo", "quux", (123, 456, 789))
        self.assertEqual(do_id, do_id2)
        self.assertEqual(mode2, Mode.switchover)

        self.assertRaises(SwitchoverExists, self.tracker.new_request, "foo", "baz", (123, 456, 789))

    def test_do_switchover(self):
        do_id, _mode = self.tracker.new_request("foo", "bar", (123, 456, 789))
        self.assertRaises(SwitchoverDoesNotExist, self.tracker.do_switchover, do_id)

        precache_path, = self.tracker._exec("select precache_path from do_requests where  id = ?", (do_id,)).fetchone()
        self.assertEqual(precache_path, "bar")

        do_id2, mode2 = self.tracker.new_request("foo", "quux", (123, 456, 789))
        self.assertEqual(do_id, do_id2)
        self.assertEqual(mode2, Mode.switchover)
        self.assertTrue(self.tracker.has_switchover(do_id))

        self.tracker.do_switchover(do_id)
        self.assertFalse(self.tracker.has_switchover(do_id))

        new_precache_path, = self.tracker._exec("select precache_path from do_requests where  id = ?", (do_id,)).fetchone()
        self.assertEqual(new_precache_path, "quux")

    def test_delete_object(self):
        do_id, _mode = self.tracker.new_request("foo", "bar", (123, 456, 789))
        self.tracker.delete_data_object(do_id)

        records, = self.tracker._exec("""
            with _counts as (
                select count(*) as c from data_objects
                union all
                select count(*) as c from do_modes
                union all
                select count(*) as c from last_access
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
