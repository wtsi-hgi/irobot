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

from abc import ABCMeta, abstractmethod
from enum import IntEnum
from numbers import Number
from typing import NamedTuple, Optional


AsyncTaskStatus = IntEnum("AsyncTaskStatus", "queued started finished unknown failed")
DataObjectState = IntEnum("DataObjectState", "data metadata checksums")

class ByteRange(NamedTuple):
    """ Byte range, inclusive, with optional checksum """
    # n.b., 0 <= start <= finish <= length; this is not enforced
    start: int
    finish: int
    checksum: Optional[str] = None

class SummaryStat(NamedTuple):
    """ Tuple of arithmetic mean and standard error """
    mean:Number
    stderr:Number

class WorkerPool(metaclass=ABCMeta):
    """ Interface for worker pools """
    @property
    @abstractmethod
    def workers(self) -> int:
        """ Number of workers in the pool """
