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
from typing import Dict, Optional, Callable, Collection

from irobot.precache.db import Datatype, SummaryStat



class AbstractDataObject(metaclass=ABCMeta):
    """ Abstract metaclass for data object active records """
    @property
    @abstractmethod
    def irods_path(self) -> str:
        """ The absolute iRODS path of the data object """

    @property
    @abstractmethod
    def status(self) -> Dict[Datatype, str]:
        """
        Status of each part of the data object's state (i.e., data,
        metadata and checksums), as a human readable string. For
        example: "Pending"; "ETA <timestamp>"; "Ready"
        """


class AbstractPrecache(Callable[[str], AbstractDataObject], Collection[AbstractDataObject], metaclass=ABCMeta):
    """
    Abstract metaclass for precache manager

    The following dunder methods must be implemented:
    * __iter__(self) -> Iterable
    * __contains__(self, irods_path:str) -> bool
    * __len__(self) -> int
    * __call__(self, irods_path:str) -> AbstractDataObject
    """
    @property
    @abstractmethod
    def commitment(self) -> int:
        """
        The total committed size of the precache, in bytes. (Note, this
        is the space currently reserved, including the size of the
        tracking DB if relevant, rather than actually used)
        """

    @property
    @abstractmethod
    def current_downloads(self) -> int:
        """ The number of currently active iGets """

    @property
    @abstractmethod
    def production_rates(self) -> Dict[Datatype, Optional[SummaryStat]]:
        """
        The production rates for the relevant part of the data object's
        state (i.e., data and checksums), as a tuple of arithmetic mean
        and standard error (or None, if not enough data exists to
        calculate these statistics)
        """
