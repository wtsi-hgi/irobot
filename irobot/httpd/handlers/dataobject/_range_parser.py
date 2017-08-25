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

import re
from typing import List, Iterable

from aiohttp.web import HTTPRequestRangeNotSatisfiable

from irobot.common import ByteRange
from irobot.httpd._error import error_factory


# Range header specification per RFC7233, section 2.1
# https://tools.ietf.org/html/rfc7233#section-2.1

_RE_RANGE_REQ = re.compile(r"""
    ^
    (?P<units> \w+ )
    =
    (?P<ranges> \d* - \d* (?: , \d* - \d* )* )
    $
""", re.IGNORECASE | re.VERBOSE)

_RE_RANGE = re.compile(r"""
    (?= .* \d )        # Must contain at least one number
    ^
    (?P<from> \d+ )?   # Range from
    -
    (?P<to> \d+ )?     # Range to
    $
""", re.VERBOSE)


def canonicalise_ranges(*ranges:Iterable[ByteRange]) -> List[ByteRange]:
    """
    Canonicalise series of ranges such that they are ordered, mutually
    exclusive and, if they overlap/juxtapose (modulo checksum), merged

    @note    Checksummed ranges can't be merged, so we assume they are
             already at least mutually exclusive in the input

    @param   ranges  At least one iterable of at least one byte range
    @return  The canonicalised list of byte ranges
    """
    assert any(ranges), "Must provide at least one iterable of at least one byte range"

    # Concatenate and sort input ranges
    prev, *remainder = sorted(r for rs in ranges for r in rs)
    merged_ranges:List[ByteRange] = []
    out_of_order = False

    # Merge
    for this in remainder:
        # TODO
        pass

    # Ensure last one gets added
    merged_ranges.append(prev)

    if out_of_order:
        # If we've split off a range's tail, then it will necessarily be
        # out of order and we'll have to run through this process again
        # to resort and potentially merge the split off range
        merged_ranges = canonicalise_ranges(merged_ranges)

    return merged_ranges


def _invalid_range(range_string:str, description:str) -> HTTPRequestRangeNotSatisfiable:
    """
    Standardised invalid range errors

    @param   range_string  Range string attempting to be parsed (string)
    @param   description   Description of the problem (string)
    @return  416 Range Not Satisfiable exception
    """
    return error_factory(416, f"Invalid range \"{range_string}\"; {description}.")

def parse_range(range_header:str, filesize:int) -> List[ByteRange]:
    """
    Parse and canonicalise the required byte range, raising a 416
    Range Not Satisfiable error if the requested range is invalid in
    any way.

    @param   range_header  Value of the range request header (string)
    @param   filesize      File size (int)
    @return  Ordered list of byte ranges, merged if overlapping (list)
    """
    req = _RE_RANGE_REQ.match(range_header)
    ranges:List[ByteRange] = []

    if not req:
        raise error_factory(416, "Could not parse range request")

    if req["units"].lower() != "bytes":
        unit = req["units"]
        raise error_factory(416, "Can only respond with byte ranges; "
                                 f"\"{unit}\" is not an understood unit.")

    # Parse the ranges
    for r in req["ranges"].split(","):
        range_match = _RE_RANGE.match(r)

        if not range_match:
            raise _invalid_range(r, "couldn't parse")

        # At least one of these exist, from our regular expression
        range_from = range_match["from"]
        range_to   = range_match["to"]

        # Three cases:
        # a-b  Range from a to b, inclusive, where a <= filesize <= b (truncated to filesize)
        # a-   Range from a to end, inclusive
        # -b   Range from end to end -b, inclusive
        new_range = ByteRange(
            int(range_from) if range_from else filesize - int(range_to),
            filesize if not all([range_from, range_to]) else min(filesize, int(range_to))
        )

        if new_range.finish > new_range.start:
            raise _invalid_range(r, "end before start")

        if new_range.start > filesize:
            raise _invalid_range(r, "out of bounds")

        ranges.append(new_range)

    return canonicalise_ranges(ranges)
