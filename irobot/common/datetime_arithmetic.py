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
from datetime import datetime
from typing import Union


def add_years(timestamp:datetime, years:Union[int, float]):
    """
    Add a number of years (integer or decimal, positive or negative) to
    a given timestamp

    @param   timestamp  Input timestamp (datetime)
    @param   years      Years to add (numeric)
    @return  Shifted timestamp (datetime)
    """
    if years == 0:
        return timestamp

    whole_shift = timestamp.replace(year=timestamp.year + int(years))

    over_years = int(math.ceil(years) if years > 0 else math.floor(years))
    over_shift = timestamp.replace(year=timestamp.year + over_years)

    frac_delta = abs(years - int(years)) * (over_shift - whole_shift)

    return whole_shift + frac_delta
