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

from functools import partial
from typing import Optional

from irobot.common import AsyncTaskStatus
from irobot.irods import Metadata


class DataObject(object):
    """ Data object """
    def __init__(self, precache_path:str, metadata:Metadata) -> None:
        """
        Constructor

        We can't subclass from NamedTuple because the data and checksum
        status properties need to be mutable

        @param   precache_path  Location in precache (string)
        @param   metadata       iRODS metadata (Metadata)
        """
        self.precache_path = precache_path
        self.metadata = metadata

        self.data_status = AsyncTaskStatus.unknown
        self.checksum_status = AsyncTaskStatus.unknown


class Entity(object):
    """ Precache entity """
    def __init__(self, irods_path:str, data_proxy, metadata_proxy, checksum_proxy) -> None:
        """
        Maintain the state of each precache entity and provide proxy
        methods back to the precache manager to do the donkey work

        @param   irods_path      iRODS data object path (string)
        @param   data_proxy      Precache manager data fetching function
        @param   metadata_proxy  Precache manager metadata fetching function
        @param   checksum_proxy  Precache manager checksumming function
        """
        self.master:Optional[DataObject] = None
        self.switchover:Optional[DataObject] = None

        # Manager function proxies
        self.data = partial(data_proxy, irods_path)
        self.metadata = partial(metadata_proxy, irods_path)
        self.checksum = partial(checksum_proxy, irods_path)
