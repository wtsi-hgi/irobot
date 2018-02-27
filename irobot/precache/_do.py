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

from datetime import datetime
from typing import Optional, Dict, List

from irobot.common import DataObjectState, AsyncTaskStatus, ByteRange
from irobot.irods import Metadata
from irobot.precache._types import InProgress
from irobot.precache._abc import AbstractDataObject


# TODO Flesh this out based on the usage in irobot.precache.Precache
class DataObject(AbstractDataObject):
    """ Data object state """

    @property
    def status(self) -> Dict[DataObjectState, AsyncTaskStatus]:
        raise NotImplementedError()

    @property
    def progress(self) -> Optional[InProgress]:
        raise NotImplementedError()

    @property
    def contention(self) -> int:
        raise NotImplementedError()

    @property
    def irods_path(self) -> str:
        raise NotImplementedError()

    @property
    def last_accessed(self) -> datetime:
        """ Get the DO's last access time """
        if not self._is_tracked:
            raise ValueError(f"Data object {self._irods_path} is not tracked")

        return self._last_accessed

    @property
    def metadata(self) -> Metadata:
        if self._metadata is None:
            raise ValueError(f"Metadata for {self._irods_path} not set")

        return self._metadata

    @property
    def invalid(self) -> bool:
        """ Return the DO's validity """
        return self._invalid

    @property
    def precache_path(self) -> str:
        if self._precache_path is None:
            raise ValueError(f"Precache path for {self._irods_path} not set")

        return self._precache_path

    @precache_path.setter
    def precache_path(self, path: str) -> None:
        # NOTE The data object metadata must be set before we set the
        # precache. This is because the tracking DB expects file sizes
        # in its new_request method and (besides) we'll already have got
        # the metadata to ensure it will fit in the precache.
        if self._is_tracked:
            raise ValueError(f"Data object {self._irods_path} is already tracked")

        if self._metadata is None:
            raise ValueError(f"Metadata for {self._irods_path} is not yet set in-memory")

        # TODO Attempt to set the precache path in the tracking DB. This
        # may fail with a constraint error (i.e., non-unique), but if
        # not, then we can now get the data object ID from the DB; if it
        # does fail, we handle this upstream
        raise NotImplementedError()

    @property
    def _is_tracked(self) -> bool:
        """ Whether the DO is tracked """
        return self._do_id is not None

    def __init__(self, irods_path: str, precache: "Precache") -> None:
        """
        Constructor

        @param   irods_path  iRODS data object path (string)
        @param   precache    Precache manager (Precache)
        """
        # TODO? We don't need to bring in the entirety of the precache
        # manager just for the sake of doing DB operations, etc.
        # However, for now it's just easier to do so...
        self._precache = precache
        tracker = precache.tracker

        # DataObject is an active record, so the exposed properties need
        # to update the tracking DB (where appropriate) upon setting
        self._irods_path = irods_path
        self._do_id: Optional[int] = tracker.get_data_object_id(irods_path)

        self._precache_path: Optional[str] = None
        self._metadata: Optional[Metadata] = None
        self._last_accessed: Optional[datetime] = None

        if self._is_tracked:
            # Load state from persistent storage
            self._precache_path = tracker.get_precache_path(self._do_id)
            self._last_accessed = tracker.get_last_access(self._do_id)

            # TODO Load metadata from JSON
            # TODO Load checksums from file

        # TODO Data fetching and checksum statuses
        self._precache_path_stream = None

        self._invalid = False

    def __enter__(self):
        if self._precache_path is None:
            raise ValueError("`_precache_path` property not set")
        # TODO: this is not threadsafe - document if this is acceptable
        self._precache_path_stream = open(self._precache_path, "rb")
        return self._precache_path_stream

    def __exit__(self, exc_type, exc_value, traceback):
        if self._precache_path_stream is not None:
            self._precache_path_stream.close()
            self._precache_path_stream = None

    def delete(self) -> None:
        raise NotImplementedError()

    def checksums(self, byte_range: Optional[ByteRange] = None) -> List[ByteRange]:
        raise NotImplementedError()

    def update_last_access(self) -> None:
        """ Update the DO's last access time """
        if not self._is_tracked:
            raise ValueError(f"Data object {self._irods_path} is not tracked")

        tracker = self._precache.tracker
        tracker.update_last_access(self._do_id)
        self._last_accessed = tracker.get_last_access(self._do_id)

    def refetch_metadata(self) -> None:
        # TODO Refetch metadata from iRODS and update the persistent
        # state, if the object is tracked

        # if not self._is_tracked:
        #     raise ValueError(f"Data object {self._irods_path} is not tracked")
        raise NotImplementedError()

    def invalidate(self) -> None:
        """ Invalidate the DO """
        self._invalid = True