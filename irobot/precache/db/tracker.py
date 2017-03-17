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
from collections import namedtuple
from datetime import datetime, timedelta
from enum import Enum
from os.path import dirname, join
from threading import Timer
from typing import Callable, Dict, List, Optional, Tuple

import irobot.common.canon as canon
from irobot.logging import LogWriter
from irobot.precache.db._adaptors_convertors import Adaptor, Convertor
from irobot.precache.db._dbi import Connection, apsw
from irobot.precache.db._exceptions import StatusExists, SwitchoverExists, SwitchoverDoesNotExist, PrecacheExists
from irobot.precache.db._udf import StandardError


def _nuple(n:int = 1) -> Tuple:
    """ Create an n-tuple of None """
    return (None,) * n


class Datatype(Enum):
    data       = 1
    metadata   = 2
    checksums  = 3

class Mode(Enum):
    master     = 1
    switchover = 2

class Status(Enum):
    requested  = 1
    producing  = 2
    ready      = 3


SummaryStat = namedtuple("SummaryStat", ["mean", "stderr"])
DataObjectFileStatus = namedtuple("DataObjectFileStatus", ["timestamp", "status"])


class TrackingDB(LogWriter):
    """ Tracking DB """
    def __init__(self, path:str, in_precache:bool = True, logger:Optional[logging.Logger] = None) -> None:
        """
        Constructor

        @param   path         Path to SQLite database (string)
        @param   in_precache  Whether the precache tracking DB is
                              located within the precache (bool)
        @param   logger       Logger (logging.Logger)
        """
        super().__init__(logger=logger)

        self.log(logging.INFO, f"Initialising precache tracking database in {path}")
        self.conn = Connection(path)

        self.path = path
        self.in_precache = False if path == ":memory:" else in_precache

        # Register host function hooks
        self.conn.register_aggregate_function("stderr", StandardError)
        self.conn.register_adaptor(Datatype, Adaptor.enum)
        self.conn.register_adaptor(Mode, Adaptor.enum)
        self.conn.register_adaptor(Status, Adaptor.enum)
        self.conn.register_adaptor(datetime, Adaptor.datetime)
        self.conn.register_adaptor(timedelta, Adaptor.timedelta)
        self.conn.register_convertor("DATATYPE", Convertor.enum_factory(Datatype))
        self.conn.register_convertor("MODE", Convertor.enum_factory(Mode))
        self.conn.register_convertor("STATUS", Convertor.enum_factory(Status))
        self.conn.register_convertor("TIMESTAMP", Convertor.datetime)

        schema = canon.path(join(dirname(__file__), "schema.sql"))
        self.log(logging.DEBUG, f"Initialising precache tracking database schema from {schema}")
        schema_script = open(schema, "rt").read()
        _ = self._exec(schema_script).fetchall()

        # Sanity check our enumerations for parity
        for enum_type, table in [(Datatype, "datatypes"), (Mode, "modes"), (Status, "statuses")]:
            for member in enum_type:
                assert self._exec(f"""
                    select sum(case when id = ? and description = ? then 1 else 0 end),
                           count(*)
                    from   {table}
                """, (member.value, member.name)).fetchone() == (1, len(enum_type))

        # NOTE Tracked files that are in an inconsistent state need to
        # be handled upstream; it shouldn't be done at this level. The
        # download_queue property can be used to determine this and the
        # database will sanitise files in a bad state (i.e., producing)
        # at initialisation time
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
    def production_rates(self) -> Dict[str, Optional[SummaryStat]]:
        """
        Retrieve the current production rates

        @return  Dictionary of production rates, where available (dict)
        """
        return {
            "download": None,
            "checksum": None,

            **{
                process: SummaryStat(rate, stderr)
                for process, rate, stderr
                in  self._exec("""
                    select process,
                           rate,
                           stderr
                    from   production_rates
                """)
            }
        }

    @property
    def download_queue(self) -> List[Tuple[Status, datetime, int, Mode, int]]:
        """
        Get the list of files being downloaded or waiting to be
        downloaded

        @return  List of current status, timestamp, data object, mode
                 and size in bytes, ordered by status then timestamp
        """
        return self._exec("select * from download_queue").fetchall()

    def get_data_object_id(self, irods_path:str) -> Optional[int]:
        """
        Get the ID of the data object with the given path on iRODS

        @param   irods_path  iRODS path (string)
        @return  Database ID (int; None if not found)
        """
        do_id, = self._exec("""
            select id
            from   data_objects
            where  irods_path = ?
        """, (irods_path,)).fetchone() or _nuple()
        return do_id

    def has_switchover(self, data_object:int) -> bool:
        """
        Check to see if a given data object has a switchover record

        @param   data_object  Data object ID (int)
        @return  Switchover existence (bool)
        """
        switchover_id, = self._exec("""
            select id
            from   do_modes
            where  data_object = ?
            and    mode        = 2
        """, (data_object,)).fetchone() or _nuple()

        return False if switchover_id is None else True

    def get_last_access(self, data_object:Optional[int] = None, older_than:timedelta = timedelta(0)) -> List[Tuple[int, datetime]]:
        """
        Get the list of last access times, either in totality or for a
        specific data object, optionally older than a specified duration

        @param   data_object  Data object ID (int)
        @param   older_than   Cut off duration (datetime.timedelta)
        @return  List of data object IDs and their last access time,
                 ordered chronologically (oldest first)
        """
        data_object_clause = "" if data_object is None else "and data_object = :do_id"
        sql = f"""
            select   data_object,
                     last_access
            from     last_access
            where    :now - last_access >= :age
                     {data_object_clause}
            order by last_access asc
        """

        return self._exec(sql, {
            "now":   datetime.utcnow(),
            "age":   older_than,
            "do_id": data_object
        }).fetchall()

    def update_last_access(self, data_object:int) -> None:
        """
        Set the last access time of a data object to the current time
        (defined by the database)

        @param   data_object  Data object ID (int)
        """
        self._exec("""
            begin immediate transaction;

            insert or replace into last_access (data_object)
                                        values (?);

            commit;
        """, (data_object,))

    def get_current_status(self, data_object:int, mode:Mode, datatype:Datatype) -> Optional[DataObjectFileStatus]:
        """
        Get the current status of the data object file

        @param   data_object  Data object ID (int)
        @param   mode         Mode (Mode)
        @param   datatype     File type (Datatype)
        @return  Current status (DataObjectFileStatus; None if not found)
        """
        status = self._exec("""
            select timestamp,
                   status
            from   current_status
            where  data_object = ?
            and    mode        = ?
            and    datatype    = ?
        """, (data_object, mode, datatype)).fetchone()
        return DataObjectFileStatus(*status) if status else None

    def set_status(self, data_object:int, mode:Mode, datatype:Datatype, status:Status) -> None:
        """
        Set the status of the given data object file

        @param   data_object  Data object ID (int)
        @param   mode         Mode (Mode)
        @param   datatype     File type (Datatype)
        @param   status       New status (Status)
        """
        try:
            self._exec("""
                begin immediate transaction;

                insert into status_log (dom_file, datatype, status)
                    select id,
                           :datatype,
                           :status
                    from   do_modes
                    where  data_object = :do_id
                    and    mode        = :mode;

                commit;
            """, {
                "do_id":    data_object,
                "mode":     mode,
                "datatype": datatype,
                "status":   status
            })

        except apsw.ConstraintError:
            self._exec("rollback")
            raise StatusExists(f"Data object file already has {status.name} status")

    def get_size(self, data_object:int, mode:Mode, datatype:Datatype) -> Optional[int]:
        """
        Get the size of a data object file

        @param   data_object  Data object ID (int)
        @param   mode         Mode (Mode)
        @param   datatype     File type (Datatype)
        @return  File size in bytes (int; None if not found)
        """
        size, = self._exec("""
            select size
            from   data_sizes
            join   do_modes
            on     do_modes.id          = data_sizes.dom_file
            where  do_modes.data_object = ?
            and    do_modes.mode        = ?
            and    data_sizes.datatype  = ?
        """, (data_object, mode, datatype)).fetchone() or _nuple()
        return size

    def set_size(self, data_object:int, mode:Mode, datatype:Datatype, size:int) -> None:
        """
        Set the size of a data object file

        @note    This probably doesn't need to be called externally

        @param   data_object  Data object ID (int)
        @param   mode         Mode (Mode)
        @param   datatype     File type (Datatype)
        @param   size         File size in bytes (int)
        """
        assert size >= 0

        self._exec("""
            begin immediate transaction;

            insert or replace into data_sizes(dom_file, datatype, size)
                select do_modes.id,
                       :datatype,
                       :size
                from   do_modes
                where  do_modes.data_object = :do_id
                and    do_modes.mode        = :dom_id;

            commit;
        """, {
            "do_id":    data_object,
            "dom_id":   mode,
            "datatype": datatype,
            "size":     size
        })

    def new_request(self, irods_path:str, precache_path:str, sizes:Tuple[int, int, int]) -> Tuple[int, Mode]:
        """
        Track a new data object or a new switchover therefor (the
        database will handle setting most of the state via triggers)

        @param   irods_path     iRODS data object path (string)
        @param   precache_path  Precache path (string)
        @param   sizes          Size in bytes of the data, metadata and
                                checksum files (tuple)
        @return  Data object ID and mode (tuple)
        """
        existing_id = self.get_data_object_id(irods_path)

        if existing_id:
            # Create a switchover record, if it doesn't already exist
            try:
                self._exec("""
                    begin immediate transaction;

                    insert into do_modes (data_object, mode, precache_path)
                                  values (?, ?, ?);

                    commit;
                """, (existing_id, Mode.switchover, precache_path))

                do_id = existing_id
                do_mode = Mode.switchover

            except apsw.ConstraintError:
                self._exec("rollback")

                if self.has_switchover(existing_id):
                    raise SwitchoverExists(f"Switchover already exists for {irods_path}")

                raise PrecacheExists(f"Cannot create switchover; precache entity in {precache_path} already exists")

        else:
            # Create a new record
            (do_id,), *_ = self._exec("""
                begin immediate transaction;

                insert into do_requests (irods_path,  precache_path)
                                 values (:irods_path, :precache_path);

                select id
                from   data_objects
                where  irods_path = :irods_path;

                commit;
            """, {
                "irods_path":    irods_path,
                "precache_path": precache_path
            }).fetchall()

            do_mode = Mode.master

        # Set file sizes
        for datatype, size in zip(Datatype, sizes):
            self.set_size(do_id, do_mode, datatype, size)

        return do_id, do_mode

    def do_switchover(self, data_object:int) -> None:
        """
        Switchover to master (the database will handle the cascade)

        @param   data_object  Data object ID
        """
        if not self.has_switchover(data_object):
            raise SwitchoverDoesNotExist("No switchover available")

        self._exec("""
            begin immediate transaction;

            delete
            from   do_modes
            where  data_object = :do_id
            and    mode        = 1;

            update do_modes
            set    mode        = 1
            where  data_object = :do_id
            and    mode        = 2;

            commit;
        """, {"do_id": data_object})

    def delete_data_object(self, data_object:int) -> None:
        """
        Delete a data object from the database in its entirety (the
        database will handle the cascade)

        @param   data_object  Data object ID
        """
        self._exec("""
            begin immediate transaction;

            delete
            from   data_objects
            where  id = ?;

            commit;
        """, (data_object,))
