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
from datetime import datetime, timedelta
from fractions import Fraction
from types import IntType, FloatType


def multiply_timedelta(delta, m):
    """
    Multiply a timedelta by m, where m can be decimal
    
    @note    Python 2.7 only supports multiplication and division of
             timedelta by integers

    @param   delta  Input timedelta (timedelta)
    @param   m      Multiplier (numeric)
    @return  Multiplied timedelta (timedelta)
    """
    try:
        assert isinstance(delta, timedelta), "Expecting timedelta, not %s" % type(timedelta)
        assert type(m) in [IntType, FloatType], "Expecting numeric multiplier, not %s" % type(m)
    except AssertionError as e:
        raise TypeError(e.message)

    frac_m = Fraction(m).limit_denominator(1000)
    return (delta * frac_m.numerator) / frac_m.denominator


def add_years(timestamp, years):
    """
    Add a number of years (integer or decimal, positive or negative) to
    a given timestamp

    @param   timestamp  Input timestamp in UTC (datetime)
    @param   years      Years to add (numeric)
    @return  Shifted timestamp in UTC (datetime)
    """
    try:
        assert isinstance(timestamp, datetime), "Expecting datetime, not %s" % type(timestamp)
        assert type(years) in [IntType, FloatType], "Expecting numeric shift, not %s" % type(years)
    except AssertionError as e:
        raise TypeError(e.message)

    if years == 0:
        return timestamp

    whole_shift = timestamp.replace(year = timestamp.year + int(years))

    over_years = int(math.ceil(years) if cmp(years, 0) == 1 else math.floor(years))
    over_shift = timestamp.replace(year = timestamp.year + over_years)

    frac_years = abs(years - int(years))
    frac_delta = multiply_timedelta(over_shift - whole_shift, frac_years)

    return whole_shift + frac_delta
