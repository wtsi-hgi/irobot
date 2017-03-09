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

import datetime as stdlib_datetime
import enum as stdlib_enum
from typing import Any, Callable, ClassVar


class Adaptor(object):
    """ Convenience namespace for adaptors """
    @staticmethod
    def datetime(dt:stdlib_datetime.datetime) -> int:
        """
        datetime.datetime adaptor

        @param   dt  Datetime (datetime.datetime)
        @return  Unix timestamp (int)
        """
        return int(dt.replace(tzinfo=stdlib_datetime.timezone.utc).timestamp())

    @staticmethod
    def timedelta(d:stdlib_datetime.timedelta) -> float:
        """
        datetime.timedelta adaptor

        @param   d  Time delta (datetime.timedelta)
        @return  Seconds (float)
        """
        return d.total_seconds()

    @staticmethod
    def enum(e:stdlib_enum.Enum) -> Any:
        """
        Enum adaptor

        @param   e  Some enum value (Enum)
        @return  Enum's value
        """
        return e.value


class Convertor(object):
    """ Convenience namespace for convertors """
    @staticmethod
    def datetime(dt:bytes) -> stdlib_datetime.datetime:
        """
        datetime.datetime convertor

        @param   dt  Datetime (bytes)
        @return  Datetime object (datetime.datetime)
        """
        return stdlib_datetime.datetime.utcfromtimestamp(int(dt))

    @staticmethod
    def timedelta(d:bytes) -> stdlib_datetime.timedelta:
        """
        datetime.timedelta convertor

        @param   d  Seconds (bytes)
        @return  Time delta object (datetime.timedelta)
        """
        return stdlib_datetime.timedelta(seconds=float(d))

    @staticmethod
    def enum_factory(enum_type:ClassVar[stdlib_enum.Enum], cast_fn:Callable[[bytes], Any] = int) -> Callable[[bytes], "enum_type"]:
        """
        Enum convertor factory

        @param   enum_type  Enum class
        @param   cast_fn    Function to cast bytes to enum values (default: int)
        @return  Enum convertor function for specific enum type (function)
        """
        def _enum_convertor(value:bytes) -> enum_type:
            return enum_type(cast_fn(value))

        return _enum_convertor
