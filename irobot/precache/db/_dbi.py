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

from collections import OrderedDict
from inspect import Parameter, signature
from typing import (Any, ClassVar, Dict, Iterator, List, Optional,
                    Sequence, Tuple, Type, Union)

import apsw

from irobot.precache.db._udf import AggregateUDF, aggregate_udf_factory_factory
from irobot.precache.db._types import Adaptor, Convertor, SQLite


# Type aliases
_PyBindings = Union[Tuple[Any, ...], Dict[str, Any]]
_SQLiteBindings = Union[Tuple[SQLite, ...], Dict[str, SQLite]]

_Adaptors = Dict[Type, Adaptor]
_Convertors = Dict[str, Convertor]


class Cursor(Iterator):
    """
    Cursor implementation that adds adaptor and convertor support to the
    default APSW cursor
    """
    def __init__(self, native_cursor:"apsw.Cursor") -> None:
        """
        Constructor
        
        @param   native_cursor  APSW Cursor
        """
        self._cursor = native_cursor

        # Get adaptors and convertors from parent connection
        conn = self._cursor.getconnection()
        self._adaptors = conn._adaptors
        self._convertors = conn._convertors

    def __iter__(self) -> "Cursor":
        return self

    def __next__(self) -> Tuple:
        """
        Fetch the next row of data from the cursor and convert values
        for any matching SQLite declarations

        @return  Row of data
        """
        data = next(self._cursor)
        desc = self._cursor.getdescription()

        return tuple(
            self._convertors.get(type_decl, lambda x: x)(value)
            for value, (_col_name, type_decl)
            in  zip(data, desc)
        )

    def _adapt_pyval(self, pyval:Any) -> SQLite:
        """
        Adapt a Python value to a native SQLite type

        @param   pyval  Python value
        @return  Native SQLite value
        """
        pytype = type(pyval)

        if pyval is None or pytype in [str, bytes, int, float]:
            # Pass through already native types
            return pyval

        try:
            # Try to adapt non-native types
            return self._adaptors[pytype](pyval)

        except KeyError:
            raise TypeError(f"No adaptor for {pytype.__name__} type")

    def _adapt_bindings(self, bindings:_PyBindings) -> _SQLiteBindings:
        """
        Adapt bind variables to native SQLite types

        @param   bindings  Bind variables (Python types)
        @return  Bind variables (SQLite types)
        """
        if isinstance(bindings, Tuple):
            return tuple(map(self._adapt_pyval, bindings))

        elif isinstance(bindings, Dict):
            return {k:self._adapt_pyval(v) for k, v in bindings.items()}

        else:
            raise TypeError("Invalid bindings; should be a tuple or dictionary")

    def execute(self, sql:str, bindings:Optional[_PyBindings] = None) -> "Cursor":
        """
        Executes the SQL statements with the specified bindings

        @param   sql       SQL statements (string)
        @param   bindings  Bind variables
        @return  Cursor to execution
        """
        sqlite_bindings = self._adapt_bindings(bindings) if bindings else None
        return Cursor(self._cursor.execute(sql, sqlite_bindings))

    def executemany(self, sql:str, binding_seq:Sequence[_PyBindings]) -> "Cursor":
        """
        Executes the SQL statements with a sequence of bindings

        @param   sql          SQL statements (string)
        @param   binding_seq  Sequence of bind variables
        @return  Cursor to execution
        """
        sqlite_binding_seq = [self._adapt_bindings(v) for v in binding_seq]
        return Cursor(self._cursor.executemany(sql, sqlite_binding_seq))

    def fetchone(self) -> Optional[Tuple]:
        """
        Fetch the next row of data from the cursor

        @return  Row of data (tuple; None on no more data)
        """
        try:
            return next(self)

        except StopIteration:
            return None

    def fetchall(self) -> List[Tuple]:
        """
        Fetch all the remaining rows of data from the cursor

        @return  Rows of data (list)
        """
        return list(self)


class Connection(apsw.Connection):
    """
    Subtyped APSW connection that allows us to register adaptors and
    convertors and which returns a cursor that supports them, as well as
    a more convenient interface for registering aggregate UDFs
    """
    def __init__(self, *args, **kwargs) -> None:
        """ Constructor """
        super().__init__(*args, **kwargs)
        self._adaptors:_Adaptors = {}
        self._convertors:_Convertors = {}

    def cursor(self) -> Cursor:
        """
        Create a new cursor on this connection

        @return  Cursor
        """
        return Cursor(super().cursor())

    def register_aggregate_function(self, name:str, udf:ClassVar[AggregateUDF]) -> None:
        """
        Register an aggregation function using an AggregateUDF
        implementation

        @param   udf  Aggregate function implementation (AggregateUDF)
        """
        # The first parameter is self, so we cut that off
        param_kinds = list(map(lambda x: x.kind,
                               list(OrderedDict(signature(udf.step).parameters).values())[1:]))

        if any(p in [Parameter.KEYWORD_ONLY, Parameter.VAR_KEYWORD] for p in param_kinds):
            raise TypeError(f"Aggregate function {udf.__name__} has an invalid step signature")

        num_args = -1 if any(p == Parameter.VAR_POSITIONAL for p in param_kinds) else len(param_kinds)

        assert len(name) < 255, f"\"{name}\" name is too long for aggregate function"
        self.createaggregatefunction(name, aggregate_udf_factory_factory(udf), num_args)

    def register_adaptor(self, t:Type, adaptor:Adaptor) -> None:
        """
        Register a type adaptor

        @param   t        Type
        @param   adaptor  Adaptor function (callable)
        """
        self._adaptors[t] = adaptor

    def register_convertor(self, decl:str, convertor:Convertor) -> None:
        """
        Register a type convertor

        @param   decl       Declared type (string)
        @param   convertor  Convertor function (callable)
        """
        self._convertors[decl] = convertor
