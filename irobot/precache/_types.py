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
from typing import Optional, Tuple

from irobot.common import ISO8601_UTC, SummaryStat


ByteRange = Optional[Tuple[int, int]]  # 0 <= from < to <= data size; None for everything
ByteRangeChecksum = Tuple[ByteRange, str]


class PrecacheFull(Exception):
    """ Exception raised when the precache is full and can't be GC'd """


class InProgress(Exception):
    """ Interrupt raised when data fetching is in progress """
    def __init__(self, size:int, started:datetime, rate:SummaryStat, *args, **kwargs) -> None:
        """
        Constructor

        @param   size     File size (int bytes)
        @param   started  Start time (datetime)
        @param   rate     Fetching rate (SummaryStat)
        """
        rate_mean, rate_stderr = rate
        self._eta = started + timedelta(seconds=size / rate_mean), int(rate_stderr)
        super().__init__(*args, **kwargs)

    @property
    def eta(self) -> Tuple[datetime, int]:
        """
        ETA for data

        @return  Tuple of ETA (datetime) and standard error of seconds (int)
        """
        return self._eta

    def __str__(self) -> str:
        """ ETA string representation """
        eta, stderr = self._eta
        return datetime.strftime(eta, ISO8601_UTC) + f" +/- {stderr}"
