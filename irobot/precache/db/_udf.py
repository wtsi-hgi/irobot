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

import math
from abc import ABCMeta, abstractmethod, abstractproperty
from typing import Callable, Optional
from numbers import Number

from irobot.precache.db._types import SQLite


class AggregateUDF(metaclass=ABCMeta):
    """ Metaclass for aggregate user-defined functions """
    @abstractproperty
    def name(self) -> str:
        """ Aggregate UDF's name in SQLite """

    @abstractmethod
    def step(self, *args) -> None:
        """ Step function """

    @abstractmethod
    def finalise(self) -> SQLite:
        """ Finalise function """

    def __call__(self) -> Callable:
        """
        Create the aggregate UDF factory for APSW

        @return  Aggregate UDF factory
        """
        def _step(_context, *args) -> None:
            self.step(*args)

        def _finalise(_context) -> SQLite:
            return self.finalise()

        return lambda: (self, _step, _finalise)

## Implementations #####################################################

class StandardError(AggregateUDF):
    """ Calculate the standard error using Welford's algorithm """
    def __init__(self) -> None:
        self.n     = 0
        self.mean  = 0.0
        self.mean2 = 0.0

    @property
    def name(self) -> str:
        return "stderr"

    def step(self, datum:Number) -> None:
        if not isinstance(datum, Number):
            # Pass over non-numeric input
            return None

        self.n += 1
        delta = datum - self.mean
        self.mean += delta / self.n
        delta2 = datum - self.mean
        self.mean2 += delta * delta2

    def finalise(self) -> Optional[float]:
        if self.n < 2:
            return None

        return math.sqrt(self.mean2 / (self.n * (self.n - 1)))
