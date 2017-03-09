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

from typing import Any, Callable, Dict, Tuple, Type, Union

# Type aliases for SQLite and interoperability with Python
SQLite = Union[str, bytes, int, float, None]
PyBindings = Union[Tuple[Any, ...], Dict[str, Any]]
SQLiteBindings = Union[Tuple[SQLite, ...], Dict[str, SQLite]]

Adaptor = Callable[[Any], SQLite]
Adaptors = Dict[Type, Adaptor]

Convertor = Callable[[bytes], Any]
Convertors = Dict[str, Convertor]
