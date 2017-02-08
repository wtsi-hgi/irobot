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

from ConfigParser import ParsingError
from types import IntType, StringType

from irobot.common import type_check_arguments, type_check_return


@type_check_return(IntType)
@type_check_arguments(max_connections=StringType)
def _parse_max_connections(max_connections):
    """
    Parse maximum connections

    @param   max_connections  Maximum concurrent connections (string)
    @return  Maximum concurrent connections (int)
    """
    value = int(max_connections)

    if value <= 0:
        raise ParsingError("Maximum number of connections must be greater than zero")

    return value


class iRODSConfig(object):
    """ iRODS configuration """
    @type_check_arguments(max_connections=StringType)
    def __init__(self, max_connections):
        """
        Parse iRODS configuration

        @param   max_connections  Maximum concurrent connections (string)
        """
        self._max_connections = _parse_max_connections(max_connections)

    @type_check_return(IntType)
    def max_connections(self):
        """
        Get maximum concurrent connections

        @return  Maximum concurrent connections (int)
        """
        return self._max_connections
