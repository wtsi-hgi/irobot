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
from abc import ABCMeta, abstractmethod, abstractproperty
from collections import OrderedDict
from enum import Enum
from datetime import datetime, timezone
from inspect import Parameter, signature
from numbers import Number
from typing import (Any, Callable, ClassVar, Dict, Iterator, List,
                    Optional, Sequence, Tuple, Type, Union)

import apsw


# Type aliases for SQLite and interoperability with Python
_SQLiteT = Union[str, bytes, int, float, None]
_PyBindingsT = Union[Tuple[Any, ...], Dict[str, Any]]
_SQLiteBindingsT = Union[Tuple[_SQLiteT, ...], Dict[str, _SQLiteT]]

_AdaptorT = Callable[[Any], _SQLiteT]
_AdaptorsT = Dict[Type, _AdaptorT]

_ConvertorT = Callable[[bytes], Any]
_ConvertorsT = Dict[str, _ConvertorT]


# Some standard adaptors and convertors
def datetime_adaptor(dt:datetime) -> int:
    """
    datetime.datetime adaptor

    @param   dt  Datetime (datetime.datetime)
    @return  Unix timestamp (int)
    """
    return int(dt.replace(tzinfo=timezone.utc).timestamp())

def datetime_convertor(dt:bytes) -> datetime:
    """
    datetime.datetime convertor

    @param   dt  Datetime (bytes)
    @return  Datetime object (datetime.datetime)
    """
    return datetime.utcfromtimestamp(int(dt))

def enum_adaptor(e:Enum) -> Any:
    """
    Enum adaptor

    @param   e  Some enum value (Enum)
    @return  Enum's value
    """
    return e.value

def enum_convertor_factory(enum_type:ClassVar[Enum], cast_fn:Callable[[bytes], Any] = int) -> Callable[[bytes], "enum_type"]:
    """
    Enum convertor factory

    @param   enum_type  Enum class
    @param   cast_fn    Function to cast bytes to enum values (default: int)
    @return  Enum convertor function for specific enum type (function)
    """
    def _enum_convertor(value:bytes) -> enum_type:
        return enum_type(cast_fn(value))

    return _enum_convertor


class AggregateUDF(metaclass=ABCMeta):
    """ Metaclass for aggregate user-defined functions """
    @abstractproperty
    def name(self) -> str:
        """ Aggregate UDF's name in SQLite """
    
    @abstractmethod
    def step(self, *args) -> None:
        """ Step function """

    @abstractmethod
    def finalise(self) -> _SQLiteT:
        """ Finalise function """

def _aggregate_udf_factory_factory(udf:AggregateUDF) -> Callable:
    """
    Create the aggregate UDF factory for APSW using AggregateUDF

    @note    APSW wants a factory that takes no parameters (i.e., a
             constant), so blame that for the "factory factory"!

    @param   udf  User-defined aggregate function (AggregateUDF)
    @return  Aggregate UDF factory
    """
    def _step(context:AggregateUDF, *args) -> None:
        return context.step(*args)

    def _finalise(context:AggregateUDF) -> _SQLiteT:
        return context.finalise()

    return lambda: (udf, _step, _finalise)


class UDF(object):
    """ Namespace for UDFs """
    class StandardError(AggregateUDF):
        """
        SQLite user-defined aggregation function that calculates standard
        error using Welford's algorithm
        """
        def __init__(self) -> None:
            self.n     = 0
            self.mean  = 0.0
            self.mean2 = 0.0

        @property
        def name(self) -> str:
            return "stderr"

        def step(self, datum:Number) -> None:
            if not isinstance(datum, Number):
                # Pass over non-numeric input
                return None

            self.n += 1
            delta = datum - self.mean
            self.mean += delta / self.n
            delta2 = datum - self.mean
            self.mean2 += delta * delta2

        def finalise(self) -> Optional[float]:
            if self.n < 2:
                return None

            return math.sqrt(self.mean2 / (self.n * (self.n - 1)))


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

    def _adapt_pyval(self, pyval:Any) -> _SQLiteT:
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

    def _adapt_bindings(self, bindings:_PyBindingsT) -> _SQLiteBindingsT:
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

    def execute(self, sql:str, bindings:Optional[_PyBindingsT] = None) -> "Cursor":
        """
        Executes the SQL statements with the specified bindings

        @param   sql       SQL statements (string)
        @param   bindings  Bind variables
        @return  Cursor to execution
        """
        sqlite_bindings = self._adapt_bindings(bindings) if bindings else None
        return Cursor(self._cursor.execute(sql, sqlite_bindings))

    def executemany(self, sql:str, binding_seq:Sequence[_PyBindingsT]) -> "Cursor":
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
    convertors and which returns a cursor that supports them
    """
    def __init__(self, *args, **kwargs) -> None:
        """ Constructor """
        super().__init__(*args, **kwargs)
        self._adaptors:_AdaptorsT = {}
        self._convertors:_ConvertorsT = {}

    def cursor(self) -> Cursor:
        """
        Create a new cursor on this connection

        @return  Cursor
        """
        return Cursor(super().cursor())

    def register_aggregate_function(self, fn:ClassVar[AggregateUDF]) -> None:
        """
        Register an aggregation function using an AggregateUDF

        @param   fn  Aggregate function implementation (class)
        """
        # The first parameter is self, so we cut that off
        param_kinds = list(map(lambda x: x.kind,
                               list(OrderedDict(signature(fn.step).parameters).values())[1:]))

        if any(p in [Parameter.KEYWORD_ONLY, Parameter.VAR_KEYWORD] for p in param_kinds):
            raise TypeError(f"Aggregate function {fn.__name__} has an invalid step signature")

        num_args = -1 if any(p == Parameter.VAR_POSITIONAL for p in param_kinds) else len(param_kinds)

        udf = fn()
        assert len(udf.name) < 255, f"Aggregate function {fn.__name__} name is too long"
        self.createaggregatefunction(udf.name, _aggregate_udf_factory_factory(udf), num_args)

    def register_adaptor(self, t:Type, adaptor:_AdaptorT) -> None:
        """
        Register a type adaptor

        @param   t        Type
        @param   adaptor  Adaptor function (callable)
        """
        self._adaptors[t] = adaptor

    def register_convertor(self, decl:str, convertor:_ConvertorT) -> None:
        """
        Register a type convertor

        @param   decl       Declared type (string)
        @param   convertor  Convertor function (callable)
        """
        self._convertors[decl] = convertor
