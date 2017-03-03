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
from typing import Dict, List, Optional, Tuple

import irobot.common.canon as canon
import irobot.precache._sqlite as _sqlite
from irobot.logging import LogWriter


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

        self.path = path
        self.in_precache = False if path == ":memory:" else in_precache

        self.log(logging.INFO, f"Initialising precache tracking database in {path}")
        self.conn = conn = _sqlite.connect(path, detect_types=_sqlite.ParseTypes.ByDefinition)

        # Register host function hooks
        conn.create_aggregate("stderr", 1, _sqlite.StandardErrorUDF)
        _sqlite.sqlite3.register_adapter(Datatype, _sqlite.enum_adaptor)
        _sqlite.sqlite3.register_adapter(Mode, _sqlite.enum_adaptor)
        _sqlite.sqlite3.register_adapter(Status, _sqlite.enum_adaptor)
        _sqlite.sqlite3.register_adapter(datetime, _sqlite.datetime_adaptor)
        _sqlite.sqlite3.register_converter("DATATYPE", _sqlite.enum_convertor_factory(Datatype))
        _sqlite.sqlite3.register_converter("MODE", _sqlite.enum_convertor_factory(Mode))
        _sqlite.sqlite3.register_converter("STATUS", _sqlite.enum_convertor_factory(Status))
        _sqlite.sqlite3.register_converter("TIMESTAMP", _sqlite.datetime_convertor)

        schema = canon.path(join(dirname(__file__), "schema.sql"))
        self.log(logging.DEBUG, f"Initialising precache tracking database schema from {schema}")
        with open(schema, "rt") as schema_file:
            schema_script = schema_file.read()
        conn.executescript(schema_script)

        # Sanity check our enumerations for parity
        for enum_type, table in [(Datatype, "datatypes"), (Mode, "modes"), (Status, "statuses")]:
            for member in enum_type:
                assert conn.execute(f"""
                    select sum(case when id = ? and description = ? then 1 else 0 end),
                           count(*)
                    from   {table}
                """, (member.value, member.name)).fetchone() == (1, len(enum_type))

        # NOTE Tracked files that are in an inconsistent state need to
        # be handled upstream; it shouldn't be done at this level
        self.log(logging.INFO, "Precache tracking database ready")

        self._schedule_vacuum()
        atexit.register(self._vacuum_timer.cancel)
        atexit.register(self.conn.close)

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
        self.conn.execute("vacuum")
        self._schedule_vacuum()

    def get_commitment(self) -> int:
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
        precache_commitment, = self.conn.execute("select size from precache_commitment").fetchone() or (0,)
        return db_size + precache_commitment

    def get_production_rates(self) -> Dict[str, Optional[SummaryStat]]:
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
                in  self.conn.execute("""
                    select process,
                           rate,
                           stderr
                    from   production_rates
                """)
            }
        }

    def get_data_object_id(self, irods_path:str) -> Optional[int]:
        """
        Get the ID of the data object with the given path on iRODS

        @param   irods_path  iRODS path (string)
        @return  Database ID (int; None if not found)
        """
        do_id, = self.conn.execute("""
            select id
            from   data_objects
            where  irods_path = ?
        """, (irods_path,)).fetchone() or (None,)
        return do_id

    def get_data_object_mode_id(self, data_object:int, mode:Mode) -> Optional[int]:
        """
        Get the ID of the data object with the given mode

        @param   data_object  Data object ID (int)
        @param   mode         Mode (Mode)
        @return  Database ID (int; None if not found)
        """
        dom_id, = self.conn.execute("""
            select id
            from   do_modes
            where  data_object = ?
            and    mode = ?
        """, (data_object, mode)).fetchone() or (None,)
        return dom_id

    def get_last_access(self, data_object:Optional[int] = None, older_than:timedelta = timedelta(0)) -> List[Tuple[int, datetime]]:
        """
        Get the list of last access times, either in totality or for a
        specific data object, optionally older than a specified duration

        @param   data_object  Data object ID (int)
        @param   older_than   Cut off duration (datetime.timedelta)
        @return  List of data object IDs and their last access time,
                 ordered chronologically
        """
        sql = """
            select data_object,
                   last_access
            from   last_access
            where  ? - last_access > ?
        """
        params = (datetime.utcnow(), older_than.total_seconds())

        if not data_object is None:
            sql = sql + " and data_object = ?"
            params = params + (data_object,)

        sql = sql + " order by last_access asc"

        return self.conn.execute(sql, params).fetchall()

    def get_current_status(self, data_object:int, mode:Mode, datatype:Datatype) -> Optional[DataObjectFileStatus]:
        """
        Get the current status of the data_object file

        @param   data_object  Data object ID (int)
        @param   mode         Mode (Mode)
        @param   datatype     File type (Datatype)
        @return  Current status (DataObjectFileStatus; None if not found)
        """
        status = self.conn.execute("""
            select timestamp,
                   status
            from   current_status
            where  data_object = ?
            and    mode        = ?
            and    datatype    = ?
        """, (data_object, mode, datatype)).fetchone()
        return DataObjectFileStatus(*status) if status else None
