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


class AcceptParser(object):
    """
    Parse the HTTP Accept request header and provide an interface for
    choosing the most appropriate media type
    """
    def __init__(self, accept_header:str = "*/*") -> None:
        """
        Constructor

        @param   accept_header  The Accept request header (string)
        """
        pass

    def can_accept(self, *media_types) -> bool:
        """
        Check any of the specified media types fulfil those deemed
        acceptable by the client

        @param   media_types  Media types to check against (strings)
        @return  Acceptability (boolean)
        """
        pass

    def preferred(self, *media_types) -> str:
        """
        Determine the most preferred media type from those specified, as
        deemed by the client. In case of a tie, the order in which the
        client specifies acceptable media types will be used (i.e.,
        leftmost first)

        @param   media_types  Media types to check against (strings)
        @return  Most preferred media type (string)
        """
        pass
