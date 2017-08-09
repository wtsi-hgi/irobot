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

import os
import re
from configparser import ParsingError
from datetime import datetime, timedelta
from functools import partial
from numbers import Number
from typing import Callable, Optional, Tuple

import irobot.common.canon as canon
from irobot.common import add_years
from irobot.config._tree_builder import Configuration


def index(location:str, value:str) -> str:
    """
    Canonicalise precache tracking database name

    @param   location  Precache directory (string)
    @param   value     Tracking database filename (string)
    @return  Absolute tracking database path (string)
    """
    dirname, basename = os.path.split(value)

    if basename == "":
        raise ParsingError("Precache index must be a filename")

    if dirname == "" and basename == value:
        return os.path.join(location, value)

    return os.path.join(canon.path(dirname), basename)


def limited_size(value:str) -> int:
    """
    Canonicalise human size string to bytes

    @param   value  File size, optionally suffixed (string)
    @return  Size in bytes (int)
    """
    try:
        return canon.human_size(value)

    except ValueError:
        raise ParsingError("Could not parse file size configuration")


def unlimited_size(value:str) -> Optional[int]:
    """
    Canonicalise optionally unlimited human size string to bytes

    @param   value  File size, optionally suffixed (string)
    @return  Size in bytes (int); or None for unlimited
    """
    if value.lower() == "unlimited":
        return None

    return limited_size(value)


def _parse_expiry(value:str) -> Optional[Tuple[Number, str]]:
    """
    Canonicalise expiry time limit string

    EXPIRY := "unlimited"
            | NUMBER ( "h" | "hour" ["s"]
                     | "d" | "day"  ["s"]
                     | "w" | "week" ["s"]
                     | "y" | "year" ["s"] )

    @param   value  Expiry time limit (string)
    @return  None, for unlimited, or a tuple of value (float) and unit (string)
    """
    if value.lower() == "unlimited":
        return None

    match = re.match(r"""
        ^                     # Anchor to start of string
        (?P<quantity>
            \d+               # Integer or floating point number into
            (?: \. \d+ )?     # "quantity" group
        )
        \s*
        (?P<unit>             # Into "unit" group:
            h (?: our s?)? |  # * Hours 
            d (?: ay s?)?  |  # * Days
            w (?: eek s?)? |  # * Weeks
            y (?: ear s?)?    # * Years
        )
        $
    """, value, re.VERBOSE | re.IGNORECASE)

    if not match:
        raise ParsingError("Could not parse expiry time limit configuration")

    val = float(match.group('quantity'))
    unit = match.group('unit')[0].lower()  # First character (lowercase)

    return val, unit


def expiry(value:str) -> Callable[[datetime], Optional[datetime]]:
    """
    Canonicalise cache invalidation expiry string

    @param   value  Maximum file age (string)
    @return  A function that calculates the expiry time from a given
             point (or None, for no expiry)
    """
    value = _parse_expiry(value)

    if value is None:
        return lambda _: None

    val, unit = value

    # Years
    if unit == "y":
        return partial(add_years, years=val)

    # Hours, Days or Weeks
    dt = val * {
        "h": timedelta(hours = 1),
        "d": timedelta(days  = 1),
        "w": timedelta(weeks = 1)
    }[unit]

    return lambda t: t + dt


def age_threshold(value:Optional[str]) -> Optional[timedelta]:
    """
    Canonicalise age threshold for cache invalidation based on the logic
    for temporal invalidation, converting "year" values into a timedelta
    based on a nominal year of 365 days

    @param   value  Age threshold (sting)
    @return  None for unlimited; duration, otherwise (timedelta)
    """
    threshold = _parse_expiry(value or "unlimited")

    if threshold is None:
        return None

    val, unit = threshold
    return val * {
        "h": timedelta(hours = 1),
        "d": timedelta(days  = 1),
        "w": timedelta(weeks = 1),
        "y": timedelta(days  = 365)
    }[unit]


class PrecacheConfig(Configuration):
    pass
