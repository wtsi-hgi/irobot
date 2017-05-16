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

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

# A *lot* of moving parts come together here...
from irobot.common import AsyncTaskStatus
from irobot.config.precache import PrecacheConfig
from irobot.irods import AVU, Metadata, MetadataJSONDecoder, MetadataJSONEncoder, iRODS
from irobot.logging import LogWriter
from irobot.precache._checksummer import Checksummer
from irobot.precache._dir_utils import new_name, create, delete
from irobot.precache._entity import DataObject, Entity
from irobot.precache._types import ByteRange, ByteRangeChecksum
from irobot.precache.db import (TrackingDB,
                                Datatype, Mode, Status,
                                SummaryStat, DataObjectFileStatus,
                                StatusExists, SwitchoverExists, SwitchoverDoesNotExist, PrecacheExists)


class _WorkerMetrics(object):
    """ Simple container for worker metrics """
    def __init__(self, workers:int, rate:Optional[SummaryStat] = None) -> None:
        self._workers = workers
        self.rate = rate

    @property
    def workers(self):
        return self._workers


class Precache(LogWriter):
    """ High-level precache management interface """
    def __init__(self, precache_config:PrecacheConfig, irods:iRODS, logger:Optional[logging.Logger] = None) -> None:
        """
        Constructor

        @param   precache_config  Precache configuration (PrecacheConfig)
        @param   irods            iRODS interface (iRODS)
        @param   logger           Logger
        """
        super().__init__(logger=logger)
        self.log(logging.DEBUG, "Starting precache")

        self.config = precache_config

        db_in_precache = os.path.commonpath([precache_config.location, precache_config.index]) == precache_config.location
        self.tracker = TrackingDB(precache_config.index, db_in_precache, logger)

        _interface_map:Dict[Datatype, Any] = {}

        self.irods = _interface_map[Datatype.data] = irods
        # TODO We need an iRODS listener that updates the state of the
        # precache appropriately as-and-when iRODS broadcasts come in

        self.checksummer = _interface_map[Datatype.checksums] = Checksummer(precache_config, logger)
        # TODO We also need a checksummer listener, for the same reason

        # Statistics for workers
        self.worker_stats = {
            datatype: _WorkerMetrics(_interface_map[datatype], rate)
            for datatype, rate in self.tracker.production_rates.items()
        }

        if self.config.expiry(datetime.utcnow()):
            # TODO Cache expiry invalidation: We need a function that is
            # scheduled to run periodically to delete old data when we
            # have a non-trivial expiration policy
            pass

        # TODO We need a function that cleans-up/sanitises bad state on
        # initialisation
