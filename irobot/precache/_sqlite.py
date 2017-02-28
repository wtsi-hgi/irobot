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

import re
import sqlite3
from datetime import timedelta
from enum import Enum
from functools import wraps
from threading import Lock
from types import MethodType
from typing import Callable, Optional


# This is a bit of a dirty hack! We simply search SQL statements for
# keywords that indicate that they may be statements that perform a
# write operation. Unfortunately, we can't just search for SELECT
# statements, because they can appear elsewhere; similarly, we can't
# check just the first word because of WITH statements and BEGIN
# transaction blocks. It will trigger false positives whenever any of
# the keywords are part of a simple SELECT statement, but the only
# effect will be to forcibly serialise that SELECT.
_potentially_writes = re.compile("|".join(map(lambda alt: rf"(?: \b {alt} \b )", [
    r"BEGIN (?: \s+ (?: DEFERRED | IMMEDIATE | EXCLUSIVE ))? (?: \s+ TRANSACTION )?",
    r"(?: COMMIT | END ) (?: \s+ TRANSACTION )?",
    r"ROLLBACK (?: \s+ TRANSACTION )?",
    r"(?: INSERT | REPLACE | (?: INSERT \s+ OR \s+ (?: REPLACE | ROLLBACK | ABORT | FAIL | IGNORE ))) \s+ INTO \s+ (?: (?: \w+ \. )? \w+ )",
    r"PRAGMA \s+ (?: (?: \w+ \. )? \w+ )",
    r"REINDEX",
    r"SAVEPOINT \s+ \w+",
    r"RELEASE (?: \s+ SAVEPOINT )? \s+ \w+",
    r"UPDATE (?: \s+ OR \s+ (?: ROLLBACK | ABORT | REPLACE | FAIL | IGNORE ))? \s+ (?: (?: \w+ \. )? \w+ ) \s+ SET",
    r"VACUUM",
    r"CREATE (?: \s+ UNIQUE )? \s+ INDEX (?: \s+ IF \s+ NOT \s+ EXISTS )? \s+ (?: (?: \w+ \. )? \w+ ) \s+ ON \s+ \w+",
    r"CREATE (?: \s+ TEMP (?: ORARY )?)? \s+ (?: TABLE | TRIGGER | VIEW ) (?: \s+ IF \s+ NOT \s+ EXISTS )? \s+ (?: (?: \w+ \. )? \w+ )",
    r"CREATE \s+ VIRTUAL \s+ TABLE (?: \s+ IF \s+ NOT \s+ EXISTS )? \s+ (?: (?: \w+ \. )? \w+ ) \s+ USING \s+ \w+",
    r"DELETE \s+ FROM \s+ (?: (?: \w+ \. )? \w+ )",
    r"DROP \s+ (?: INDEX | TABLE | TRIGGER | VIEW ) (?: IF \s+ EXISTS )? \s+ (?: (?: \w+ \. )? \w+)",
    r"ALTER \s+ TABLE \s+ (?: (?: \w+ \. )? \w+ ) \s+ (?: RENAME | ADD )",
    r"ANALYZE"
])), re.VERBOSE | re.IGNORECASE).search


class IsolationLevel(Enum):
    """ SQLite3 isolation levels """
    AUTOCOMMIT = None
    DEFERRED = "DEFERRED"
    IMMEDIATE = "IMMEDIATE"
    EXCLUSIVE = "EXCLUSIVE"


class TypeParser(Enum):
    """ SQLite3 type parsing constants """
    NONE = 0
    DECLTYPES = sqlite3.PARSE_DECLTYPES
    COLNAMES = sqlite3.PARSE_COLNAMES
    ALL = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES


class _ThreadSafeConnection(sqlite3.Connection):
    """ Subclass SQLite connections such that writes are serialised """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._write_lock = Lock()
        self._locked = False

        serialise_always = [self.commit, self.executemany]
        serialise_writes = [self.execute, self.executescript]

        to_serialise = list(zip(serialise_always, [True] * len(serialise_always))) \
                     + list(zip(serialise_writes, [False] * len(serialise_writes)))

        for method, always in to_serialise:
            self._serialise(method, always)
            
    def _serialise(self, method:Callable, always:bool) -> None:
        """
        Serialise methods

        @param   method  Class method (callable)
        @param   always  Always serialise, or just writes (bool)

        @note    Write serialisation will be based on the first argument
        """
        @wraps(method)
        def _serialised(_self, *args, **kwargs):
            self._acquire(None if always else args[0])
            output = method(*args, **kwargs)
            self._release()
            return output

        setattr(self, method.__name__, MethodType(_serialised, self))

    def _acquire(self, sql:Optional[str] = None) -> None:
        """
        Acquire the writing lock

        @param   sql  SQL statement (string; None for always lock)
        """
        if sql is None or _potentially_writes(sql):
            self._write_lock.acquire()
            self._locked = True

    def _release(self) -> None:
        """ Release the writing lock """
        if self._locked:
            self._write_lock.release()
            self._locked = False


def connect(database:str,
            timeout:timedelta = timedelta(seconds=5),
            detect_types:TypeParser = TypeParser.NONE,
            isolation_level:IsolationLevel = IsolationLevel.AUTOCOMMIT,
            cached_statements:int = 100,
            uri:bool = False) -> _ThreadSafeConnection:

    """ Instantiate a thread-safe connection """
    return sqlite3.connect(database=database,
                           timeout=timeout.total_seconds(),
                           detect_types=detect_types.value,
                           isolation_level=isolation_level.value,
                           check_same_thread=False,
                           factory=_ThreadSafeConnection,
                           cached_statements=cached_statements,
                           uri=uri)