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
from ConfigParser import ParsingError
from types import IntType, NoneType, StringType

from irobot.common import canonical_path, type_check_arguments, type_check_return


@type_check_return(NoneType, StringType)
@type_check_arguments(output=StringType)
def _parse_output(output):
    """
    Parse logging output destination

    @param   output  Logging destination
    """
    if output == "STDERR":
        return None

    return canonical_path(output)


@type_check_return(IntType)
@type_check_arguments(level=StringType)
def _parse_level(level):
    """
    Parse logging level

    @param   log_level  Logging level (string)
    @return  Logging level (int)
    """
    try:
        return {
            "debug":    logging.DEBUG,
            "info":     logging.INFO,
            "warning":  logging.WARNING,
            "error":    logging.ERROR,
            "critical": logging.CRITICAL
        }[level.lower()]

    except KeyError:
        raise ParsingError("Invalid logging level")


class LoggingConfig(object):
    """ Logging configuration """
    @type_check_arguments(output=StringType, level=StringType)
    def __init__(self, output, level):
        """
        Parse logging configuration

        @param   output  Logging destination
        @param   level   Logging level
        """
        self._output = _parse_output(output)
        self._level = _parse_level(level)

    @type_check_return(NoneType, StringType)
    def output(self):
        """
        Get logging output destination

        @return  Logging destination (string or None for stderr)
        """
        return self._output

    @type_check_return(IntType)
    def level(self):
        """
        Get logging level

        @return  Logging level (int)
        """
        return self._level
