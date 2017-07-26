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
from enum import Enum


AsyncTaskStatus = Enum("AsyncTaskStatus", "queued started finished unknown failed")


class WorkerPool(metaclass=ABCMeta):
    """ Interface for worker pools """
    # FIXME? Our WorkerPools are also Listenables (and LogWriters)
    @property
    @abstractmethod
    def workers(self) -> int:
        """ Number of workers in the pool """
