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
from functools import total_ordering
from typing import Dict, List


# Media type naming per RFC6838
# https://tools.ietf.org/html/rfc6838#section-4.2
RE_MEDIA_TYPE = re.compile(r"""
    # Type and subtype between 1 and 64 characters
    (?= ^ [^/]{1,64} / [^/]{1,64} $ )

    (?:^
        (?P<type>
            [a-z0-9]
            [a-z0-9!#\$&\-^_\.\+]{,126}
        )
        /
        (?P<subtype>
            [a-z0-9]
            [a-z0-9!#\$&\-^_\.\+]{,126}
        )
    $)
""", re.VERBOSE | re.IGNORECASE)

_RE_COMMA_SEP = re.compile(r"\s*,\s*")
_RE_SEMICOLON_SEP = re.compile(r"\s*;\s*")
_RE_EQUAL_SEP = re.compile(r"\s*=\s*")


@total_ordering
class _MediaRange(object):
    """ Parametrised media range """
    def __init__(self, media_range:str, **params) -> None:
        """
        Constructor

        @param   media_range  Media type or range (string)
        @param   params       Media type parameters
        """
        self.media_range = media_range
        self.q = float(params.get("q", 1.0))
        self.params = {k:v for k,v in params.items() if not k == "q"}

    def in_range(self, media_type:str, **params) -> bool:
        """
        Check the supplied media type is in the media range

        @param    media_type  Media type (string)
        @param    params      Media type parameters
        @return   Inclusion (boolean)
        """
        range_type, range_subtype = self.media_range.split("/")
        if range_type == range_subtype == "*":
            # Accept all
            return True

        _m = RE_MEDIA_TYPE.match(media_type)
        mt_type = _m["type"]
        mt_subtype = _m["subtype"]

        if mt_type == range_type and range_subtype == "*":
            # Accept any subtype
            return True

        return mt_type == range_type \
           and mt_subtype == range_subtype \
           and {k:v for k,v in params.items() if not k == "q"} == self.params

    def __str__(self) -> str:
        _builder = [
            self.media_range,
            f"q={self.q}",
            *[f"{k}={v}" for k, v in self.params.items()]
        ]
        return "; ".join(_builder)

    def __repr__(self) -> str:
        return f"<MediaRange: {self}>"

    def __eq__(self, other:"_MediaRange") -> bool:
        return self.media_range == other.media_range \
           and self.params == other.params

    def __lt__(self, other:"_MediaRange") -> bool:
        # This is not a typo :)
        return self.q > other.q


class AcceptParser(object):
    """
    Parse the HTTP Accept request header and provide an interface for
    choosing the most appropriate media type
    """
    def __init__(self, accept_header:str = "*/*") -> None:
        """
        Constructor: We assume the client sends us this correctly formed

        @param   accept_header  The Accept request header (string)
        """
        _ranges:List[_MediaRange] = []

        for m in _RE_COMMA_SEP.split(accept_header):
            media_range, *_params = _RE_SEMICOLON_SEP.split(m)
            params = dict(_RE_EQUAL_SEP.split(p) for p in _params)
            _ranges.append(_MediaRange(media_range, **params))

        # The "most acceptable" media range is the first element of the
        # list and decreases in priority; sorted is stable, so relative
        # ordering (based on the input string) is preserved
        self.media_ranges = sorted(_ranges)

    def can_accept(self, *media_types) -> bool:
        """
        Check any of the specified media types fulfil those deemed
        acceptable by the client

        TODO Should allow parametrisable media types

        @param   media_types  Media types to check against (strings)
        @return  Acceptability (boolean)
        """
        return any(r.in_range(m) for m in media_types for r in self.media_ranges)

    def preferred(self, *media_types) -> str:
        """
        Determine the most preferred media type from those specified, as
        deemed by the client. In case of a tie, the order in which the
        client specifies acceptable media types will be used (i.e.,
        leftmost first)

        TODO Should allow parametrisable media types

        @note    We presume that can_accept is true and already tested,
                 so this will always return a valid media type

        @param   media_types  Media types to check against (strings)
        @return  Most preferred media type (string)
        """
        for r in self.media_ranges:
            for m in media_types:
                if r.in_range(m):
                    return m
