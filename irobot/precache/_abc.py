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
from datetime import datetime
from typing import Dict, Optional, Callable, Collection

from irobot.common import AsyncTaskStatus, DataObjectState, SummaryStat
from irobot.irods import Metadata


class AbstractDataObject(metaclass=ABCMeta):
    """ Abstract metaclass for data object active records """

    ## iRODS and Precache Paths ########################################

    @property
    @abstractmethod
    def irods_path(self) -> str:
        """ The absolute iRODS path of the data object """

    @property
    @abstractmethod
    def precache_path(self) -> str:
        """ The absolute path to the precached data object's state """

    @precache_path.setter
    @abstractmethod
    def precache_path(self, path:str) -> None:
        """ Precache path setter """

    ## Data Object Status ##############################################

    @property
    @abstractmethod
    def status(self) -> Dict[DataObjectState, AsyncTaskStatus]:
        """
        Status of each part of the data object's state (i.e., data,
        metadata and checksums)
        """

    @property
    @abstractmethod
    def contention(self) -> int:
        """ The number of active connections to the data object """

    ## Last Access Time ################################################

    @property
    @abstractmethod
    def last_accessed(self) -> datetime:
        """ Last accessed timestamp (UTC) """

    @abstractmethod
    def update_last_access(self) -> None:
        """ Update the last access timestamp to now """

    ## Metadata ########################################################

    @property
    @abstractmethod
    def metadata(self) -> Metadata:
        """ The iRODS filesystem and AVU metadata for the data object """

    @abstractmethod
    def refetch_metadata(self) -> Metadata:
        """ Forcibly refetch the iRODS metadata for the data object """

    ## Methods #########################################################

    @abstractmethod
    def delete(self) -> None:
        """ Delete data object (i.e., self) from the precache """


class AbstractPrecache(Callable[[str], AbstractDataObject], Collection[AbstractDataObject], metaclass=ABCMeta):
    """
    Abstract metaclass for precache manager

    The following dunder methods must be implemented:
    * __iter__(self) -> Iterable
    * __contains__(self, irods_path:str) -> bool
    * __len__(self) -> int
    * __call__(self, irods_path:str) -> AbstractDataObject

    NOTE Mapping may be better than Callable + Collection, implementing
    __getitem__ instead of the "unusual" __call__, but then we'd also
    have to implement keys, items, values, get, __eq__ and __ne__...

    NOTE __call__ is expected to raise the following exceptions:
    * InProgress         When a data object is still being fetched
    * FileNotFoundError  When the data object doesn't exist on iRODS
    * PermissionError    When the user doesn't have access to the data object on iRODS
    * IOError            When some other iRODS problem occurs
    * PrecacheFull       When the precache is full
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
    def production_rates(self) -> Dict[DataObjectState, Optional[SummaryStat]]:
        """
        The production rates for the relevant part of the data object's
        state (i.e., data and checksums), as a tuple of arithmetic mean
        and standard error (or None, if not enough data exists to
        calculate these statistics)
        """
