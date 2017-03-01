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
from datetime import datetime, timedelta
from enum import Enum
from os.path import dirname, join
from threading import Timer
from typing import Optional

import irobot.common.canon as canon
import irobot.precache._sqlite as _sqlite
from irobot.logging import LogWriter


class _Datatype(Enum):
    data       = 1
    metadata   = 2
    checksums  = 3

class _Mode(Enum):
    master     = 1
    switchover = 2

class _Status(Enum):
    requested  = 1
    producing  = 2
    ready      = 3
    


class TrackingDB(LogWriter):
    """ Tracking DB """
    def __init__(self, path:str, logger:Optional[logging.Logger] = None) -> None:
        """
        Constructor

        @param   path    Path to SQLite database (string)
        @param   logger  Logger
        """
        super().__init__(logger=logger)

        self.path = path

        self.log(logging.INFO, f"Initialising precache tracking database in {path}")
        self.conn = conn = _sqlite.connect(path, detect_types=_sqlite.ParseTypes.ByDefinition)
        conn.create_aggregate("stderr", 1, _sqlite.StandardErrorUDF)
        _sqlite.sqlite3.register_adapter(datetime, _sqlite.datetime_adaptor)
        _sqlite.sqlite3.register_converter("TIMESTAMP", _sqlite.datetime_convertor)

        schema = canon.path(join(dirname(__file__), "schema.sql"))
        self.log(logging.DEBUG, f"Initialising precache tracking database schema from {schema}")
        with open(schema, "rt") as schema_file:
            schema_script = schema_file.read()
        conn.executescript(schema_script)

        # Sanity check our enumerations
        for enum_type, table in [(_Datatype, "datatypes"), (_Mode, "modes"), (_Status, "statuses")]:
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

    def __del__(self) -> None:
        """ Cancel the vacuum timer on GC """
        if self._vacuum_timer.is_alive():
            self._vacuum_timer.cancel()

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
