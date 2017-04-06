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
from typing import Optional

from irobot.config.precache import PrecacheConfig
from irobot.logging import LogWriter
from irobot.precache._checksummer import ChecksumStatus, Checksummer
from irobot.precache.db import TrackingDB


class Precache(LogWriter):
    """ High level precache interface """
    def __init__(self, precache_config:PrecacheConfig, logger:Optional[logging.Logger] = None) -> None:
        """
        Constructor

        @param   precache_config  Precache configuration (PrecacheConfig)
        @param   logger           Logger
        """
        super().__init__(logger=logger)
        self.config = precache_config

        self.checksummer = Checksummer(precache_config, logger)

        db_in_precache = os.path.commonpath([precache_config.location, precache_config.index]) == precache_config.location
        self.tracker = TrackingDB(precache_config.index, db_in_precache, logger)
