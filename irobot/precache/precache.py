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

import atexit
import logging
import os
from datetime import datetime, timedelta
from threading import Lock, Timer
from typing import Dict, List, Iterable, Optional

# A *lot* of moving parts come together here...
from irobot.common import DataObjectState, SummaryStat
from irobot.config import PrecacheConfig
from irobot.irods import iRODS
from irobot.logs import LogWriter
from irobot.precache._abc import AbstractPrecache
from irobot.precache._checksummer import Checksummer
from irobot.precache._dir_utils import delete
from irobot.precache._do import DataObject
from irobot.precache._types import PrecacheFull, InProgress, InProgressWithETA
from irobot.precache.db import TrackingDB, DataObjectFileStatus, StatusExists, PrecacheExists


class _WorkerMetrics(object):
    """ Simple container for worker metrics """
    def __init__(self, workers: int, rate: Optional[SummaryStat]=None) -> None:
        self._workers = workers
        self.rate = rate

    @property
    def workers(self) -> int:
        return self._workers


class Precache(AbstractPrecache, LogWriter):
    """ High-level precache management interface """
    def __init__(self, precache_config: PrecacheConfig, irods: iRODS, logger: Optional[logging.Logger]=None) -> None:
        """
        Constructor

        @param   precache_config  Precache configuration (PrecacheConfig)
        @param   irods            iRODS interface (iRODS)
        @param   logger           Logger
        """
        super().__init__(logger=logger)
        self.log(logging.INFO, "Starting precache")

        self.config = precache_config

        db_in_precache = os.path.commonpath(
            [precache_config.location, precache_config.index]) == precache_config.location
        self.tracker = TrackingDB(precache_config.index, db_in_precache, logger)

        # In-memory representation of the precache
        self.data_objects: Dict[str, DataObject] = {}
        self._do_lock = Lock()

        # TODO We need a function that cleans-up/sanitises bad state on
        # initialisation

        self.irods = irods
        # TODO We need an iRODS listener that updates the state of the
        # precache appropriately as-and-when iRODS broadcasts come in

        self.checksummer = Checksummer(precache_config, logger)
        # TODO We also need a checksummer listener, for the same reason

        # Statistics for workers
        self.worker_stats = {
            DataObjectState.data: _WorkerMetrics(self.irods.workers),
            DataObjectState.checksums: _WorkerMetrics(self.checksummer.workers)
        }
        self._update_worker_stats()

        # Garbage collection setup
        self.temporal_gc = self.config.expiry(datetime.utcnow()) is not None
        self.capacity_gc = self.config.size is not None and self.config.age_threshold is not None

        if self.temporal_gc:
            # FIXME? This is a bit contrived :P i.e., GC period is half
            # the temporal expiry limit...
            now = datetime.utcnow()
            self._gc_period = (self.config.expiry(now) - now) / 2

            self._schedule_temporal_gc()
            atexit.register(self._gc_timer.cancel)

    def __del__(self) -> None:
        """ Cancel any running timers on Python GC """
        if self.temporal_gc and self._gc_timer.is_alive():
            self._gc_timer.cancel()

        if self._update_stats_timer.is_alive():
            self._update_stats_timer.cancel()

    def _schedule_temporal_gc(self) -> None:
        """ Initialise and start the GC timer """
        self._gc_timer = Timer(self._gc_period.total_seconds(), self._gc)
        self._gc_timer.daemon = True
        self._gc_timer.start()

    def _gc(self) -> None:
        """ Garbage collect invalidated entries from the precache """
        with self._do_lock:
            self.log(logging.DEBUG, "Running precache garbage collection")
            gc_time = datetime.utcnow()

            # Data objects marked as invalid or expired (if appropriate)
            to_gc = [
                irods_path
                for irods_path, do in self.data_objects.items()
                if do.invalid or (self.temporal_gc and gc_time > self.config.expiry(do.last_accessed))
            ]

            # Garbage collect
            for irods_path in to_gc:
                self.log(logging.DEBUG, f"Garbage collecting {irods_path} from precache")

                do = self.data_objects[irods_path]
                do_id = self.tracker.get_data_object_id(irods_path)

                self.tracker.delete_data_object(do_id)
                delete(do.precache_path)
                del self.data_objects[irods_path]

        if self.temporal_gc:
            self._schedule_temporal_gc()

    def _update_worker_stats(self, period: timedelta=timedelta(minutes=15)) -> None:
        """
        Update the worker production stats, if available, and refresh
        them periodically.

        @param   period  Refresh period (timedelta; default 15 minutes)
        """
        for datatype, rate in self.tracker.production_rates.items():
            if rate:
                self.worker_stats[datatype].rate = rate

        # Schedule next update
        self._update_stats_timer = Timer(period.total_seconds(), self._update_worker_stats, [period])
        self._update_stats_timer.daemon = True
        self._update_stats_timer.start()

    def __call__(self, irods_path: str) -> DataObject:
        # Convenience wrapper
        return self.get_data_object(irods_path)

    def get_data_object(self, irods_path: str) -> DataObject:
        """
        TODO
        """
        raise NotImplementedError()

    def accommodate(self, accommodation: int) -> None:
        """
        Attempt to invalidate data objects to fulfil the specified space
        requirements. Data objects will only be invalidated if the
        accommodation can be fulfilled (in which case, the garbage
        collector will be invoked automatically), otherwise a
        PrecacheFull exception will be raised.

        @note    This function should only be called if capacity GC is
                 enabled (i.e., both the precache size and age threshold
                 are limited).

        @note    Data objects are invalidated, oldest first, until the
                 accommodation is reached.

        @note    If the accommodation can't be reached, then
                 invalidation is cancelled and a PrecacheFull exception
                 will be raised.

        @param   accommodation  Required precache space in bytes (int)
        """
        with self._do_lock:
            invalidation_time = datetime.utcnow()

            to_invalidate: List[str] = []
            invalidatable = sorted([
                (irods_path, do.last_accessed, do.metadata.size)
                for irods_path, do in self.data_objects.items()
                if invalidation_time - do.last_accessed > self.config.age_threshold
            ], key=lambda x: x[1], reverse=True)

            freed_space: int = 0
            while freed_space < accommodation and invalidatable:
                irods_path, _, size = invalidatable.pop()
                to_invalidate.append(irods_path)
                freed_space += size

            if freed_space < accommodation:
                raise PrecacheFull(f"Precache cannot accommodate {accommodation} bytes")

            for do in to_invalidate:
                self.data_objects[do].invalidate()

        if to_invalidate:
            self._gc()

    def invalidate(self, irods_path: str) -> None:
        """
        Manually invalidate a data object and call the GC if needs be

        @param   irods_path  Data object iRODS path (string)
        """
        call_gc = False

        with self._do_lock:
            if irods_path in self.data_objects:
                call_gc = True
                self.data_objects[irods_path].invalidate()

        if call_gc:
            self._gc()

    def __iter__(self) -> Iterable:
        raise NotImplementedError()

    def __contains__(self, irods_path: str) -> bool:
        raise NotImplementedError()

    def __len__(self) -> int:
        raise NotImplementedError()

    @property
    def commitment(self) -> int:
        raise NotImplementedError()

    @property
    def current_downloads(self) -> int:
        raise NotImplementedError()

    @property
    def production_rates(self) -> Dict[DataObjectState, Optional[SummaryStat]]:
        raise NotImplementedError()
