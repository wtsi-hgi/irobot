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

import atexit
import logging
import os
from datetime import datetime, timedelta
from os.path import dirname, join
from threading import Timer
from typing import Callable, Dict, List, NamedTuple, Optional, Tuple

import irobot.common.canon as canon
from irobot.common import AsyncTaskStatus, DataObjectState, SummaryStat
from irobot.logs import LogWriter
from irobot.precache.db._adaptors_convertors import Adaptor, Convertor
from irobot.precache.db._dbi import Connection, apsw
from irobot.precache.db._exceptions import StatusExists, PrecacheExists
from irobot.precache.db._udf import StandardError


def _nuple(n: int=1) -> Tuple:
    """ Create an n-tuple of None """
    return (None,) * n


class DataObjectFileStatus(NamedTuple):
    timestamp: datetime
    status: AsyncTaskStatus


class TrackingDB(LogWriter):
    """ Tracking DB """

    def __init__(self, path: str, in_precache: bool=True, logger: Optional[logging.Logger]=None) -> None:
        """
        Constructor

        @param   path         Path to SQLite database (string)
        @param   in_precache  Whether the precache tracking DB is
                              located within the precache (bool)
        @param   logger       Logger (logging.Logger)
        """
        super().__init__(logger=logger)

        self.log(logging.DEBUG, f"Initialising precache tracking database in {path}")

        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.conn = Connection(path)

        self.path = path
        self.in_precache = False if path == ":memory:" else in_precache

        # Register host function hooks
        self.conn.register_aggregate_function("stderr", StandardError)
        self.conn.register_adaptor(DataObjectState, Adaptor.enum)
        self.conn.register_adaptor(AsyncTaskStatus, Adaptor.enum)
        self.conn.register_adaptor(datetime, Adaptor.datetime)
        self.conn.register_adaptor(timedelta, Adaptor.timedelta)
        self.conn.register_convertor("DATATYPE", Convertor.enum_factory(DataObjectState))
        self.conn.register_convertor("STATUS", Convertor.enum_factory(AsyncTaskStatus))
        self.conn.register_convertor("TIMESTAMP", Convertor.datetime)

        schema = canon.path(join(dirname(__file__), "schema.sql"))
        self.log(logging.DEBUG, f"Initialising precache tracking database schema from {schema}")
        with open(schema, "rt") as schema_file:
            schema_script = schema_file.read()
        _ = self._exec(schema_script).fetchall()

        # Sanity check our enumerations for parity
        for enum_type, table in (DataObjectState, "datatypes"), (AsyncTaskStatus, "statuses"):
            for member in enum_type:
                assert self._exec(f"""
                    select sum(case when id = ? and description = ? then 1 else 0 end),
                           count(*)
                    from   {table}
                """, (member.value, member.name)).fetchone() == (1, len(enum_type))

        # NOTE Tracked files that are in an inconsistent state need to
        # be handled upstream; it shouldn't be done at this level,
        # although the database will sanitise files in a bad state
        # (i.e., producing) at initialisation time
        self.log(logging.INFO, "Precache tracking database ready")

        self._schedule_vacuum()
        atexit.register(self._vacuum_timer.cancel)
        atexit.register(self.conn.close)

    @property
    def _exec(self) -> Callable:
        """
        Convenience property to create a new cursor and return its
        execute method; now we can do self._exec(...) instead
        """
        return self.conn.cursor().execute

    def __del__(self) -> None:
        """ Cancel the vacuum timer and close the connection on GC """
        if self._vacuum_timer.is_alive():
            self._vacuum_timer.cancel()

        self.conn.close()

    def _schedule_vacuum(self) -> None:
        """ Initialise and start the vacuum timer """
        self._vacuum_timer = Timer(timedelta(hours=12).total_seconds(), self._vacuum)
        self._vacuum_timer.daemon = True
        self._vacuum_timer.start()

    def _vacuum(self) -> None:
        """ Vacuum the database """
        self.log(logging.DEBUG, "Vacuuming precache tracking database")
        self._exec("vacuum")
        self._schedule_vacuum()

    @property
    def commitment(self) -> int:
        """
        Retrieve the amount of space used/reserved by the precache
        (including the size of the tracking DB, when relevant)

        @note    This represents the actual size of used/reserved in the
                 precache, rather than the physical size on disk (i.e.,
                 modulo device block size). As such, it will generally
                 be an underestimate.

        @return  Precache commitment (int)
        """
        db_size = os.stat(self.path).st_size if self.in_precache else 0
        precache_commitment, = self._exec("select size from precache_commitment").fetchone()

        return db_size + precache_commitment

    @property
    def production_rates(self) -> Dict[DataObjectState, Optional[SummaryStat]]:
        """
        Retrieve the current production rates

        @return  Dictionary of production rates, where available (dict)
        """
        return {
            DataObjectState.data: None,
            DataObjectState.checksums: None,

            **{
                process: SummaryStat(rate, stderr)
                for process, rate, stderr
                in self._exec("""
                    select process,
                           rate,
                           stderr
                    from   production_rates
                """)
            }
        }

    @property
    def precache_entities(self) -> List[int]:
        """
        Get the list of data object IDs that are currently tracked in
        the precache database

        @return  List of data object IDs
        """
        ids = self._exec("select id from data_objects").fetchall()
        return [id for id, in ids]

    def get_data_object_id(self, irods_path: str) -> Optional[int]:
        """
        Get the ID of the data object with the given path on iRODS

        @param   irods_path  iRODS path (string)
        @return  Data object ID (int; None if not found)
        """
        do_id, = self._exec("""
            select id
            from   data_objects
            where  irods_path = ?
        """, (irods_path,)).fetchone() or _nuple()
        return do_id

    def get_precache_path(self, data_object: int) -> Optional[str]:
        """
        Get the precache path of the data object

        @param   data_object  Data object ID (int)
        @return  Precache path (string; None if not found)
        """
        precache_path, = self._exec("""
            select precache_path
            from   data_objects
            where  id = ?
        """, (data_object,)).fetchone() or _nuple()
        return precache_path

    def get_last_access(self, data_object: int) -> Optional[datetime]:
        """
        Get the last access time of the data object

        @param   data_object  Data object ID (int)
        @return  Last access time (datetime; None if not found)
        """
        last_access, = self._exec("""
            select last_access
            from   data_objects
            where  id = ?
        """, (data_object,)).fetchone() or _nuple()
        return last_access

    def update_last_access(self, data_object: int) -> None:
        """
        Set the last access time of a data object to the current time,
        per the database's definition

        @param   data_object  Data object ID (int)
        """
        self._exec("""
            begin immediate transaction;

            update data_objects
            set    last_access = strftime('%s', 'now')
            where  id = ?;

            commit;
        """, (data_object,))

    def get_current_status(self, data_object: int, datatype: DataObjectState) -> Optional[DataObjectFileStatus]:
        """
        Get the current status of the data object file

        @param   data_object  Data object ID (int)
        @param   datatype     File type (DataObjectState)
        @return  Current status (DataObjectFileStatus; None if not found)
        """
        status = self._exec("""
            select timestamp,
                   status
            from   current_status
            where  data_object = ?
            and    datatype    = ?
        """, (data_object, datatype)).fetchone()
        return DataObjectFileStatus(*status) if status else None

    def set_status(self, data_object: int, datatype: DataObjectState, status: AsyncTaskStatus) -> None:
        """
        Set the status of the given data object file

        @param   data_object  Data object ID (int)
        @param   datatype     File type (DataObjectState)
        @param   status       New status (AsyncTaskStatus)
        """
        try:
            self._exec("""
                begin immediate transaction;

                insert into status_log (data_object, datatype, status)
                                values (?, ?, ?);

                commit;
            """, (data_object, datatype, status))

        except apsw.ConstraintError:
            self._exec("rollback")
            raise StatusExists(f"Data object file already has {status.name} status")

    def get_size(self, data_object: int, datatype: DataObjectState) -> Optional[int]:
        """
        Get the size of a data object file

        @param   data_object  Data object ID (int)
        @param   datatype     File type (DataObjectState)
        @return  File size in bytes (int; None if not found)
        """
        size, = self._exec("""
            select size
            from   data_sizes
            where  data_object = ?
            and    datatype    = ?
        """, (data_object, datatype)).fetchone() or _nuple()
        return size

    def set_size(self, data_object: int, datatype: DataObjectState, size: int) -> None:
        """
        Set the size of a data object file

        @note    This probably doesn't need to be called externally

        @param   data_object  Data object ID (int)
        @param   datatype     File type (DataObjectState)
        @param   size         File size in bytes (int)
        """
        assert size >= 0

        self._exec("""
            begin immediate transaction;

            insert or replace into data_sizes (data_object, datatype, size)
                                       values (?, ?, ?);

            commit;
        """, (data_object, datatype, size))

    def new_request(self, irods_path: str, precache_path: str, sizes: Tuple[int, int, int]) -> int:
        """
        Track a new data object (the database will handle setting most
        of the state via triggers)

        @param   irods_path     iRODS data object path (string)
        @param   precache_path  Precache path (string)
        @param   sizes          Size in bytes of the data, metadata and
                                checksum files (tuple)
        @return  Data object ID
        """
        existing_id = self.get_data_object_id(irods_path)

        if existing_id:
            raise PrecacheExists(f"Precache entity already exists for {irods_path}")

        try:
            # Create a new record
            (do_id,), *_ = self._exec("""
                begin immediate transaction;

                insert into data_objects (irods_path, precache_path)
                                  values (:irods_path, :precache_path);

                select id
                from   data_objects
                where  irods_path = :irods_path;

                commit;
            """, {
                "irods_path": irods_path,
                "precache_path": precache_path
            }).fetchall()

        except apsw.ConstraintError:
            self._exec("rollback")
            raise PrecacheExists(f"Precache entity already exists in {precache_path}")

        # Set file sizes
        for datatype, size in zip(DataObjectState, sizes):
            self.set_size(do_id, datatype, size)

        return do_id

    def delete_data_object(self, data_object: int) -> None:
        """
        Delete a data object from the database in its entirety (the
        database will handle the cascade)

        @param   data_object  Data object ID
        """
        self._exec("""
            begin immediate transaction;

            delete from data_objects where id = ?;

            commit;
        """, (data_object,))
