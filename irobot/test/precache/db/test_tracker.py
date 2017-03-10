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
from tempfile import NamedTemporaryFile

from irobot.precache.db import TrackingDB, Datatype, Mode, Status
from irobot.precache.db.tracker import _nuple


class TestMisc(unittest.TestCase):
    def test_nuple(self):
        self.assertEqual(_nuple(), (None,))
        self.assertEqual(_nuple(2), (None, None))
        self.assertEqual(_nuple(3), (None, None, None))


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


if __name__ == "__main__":
    unittest.main()
