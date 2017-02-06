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
from types import IntType, StringType

from irobot.common import type_check, type_check_return


@type_check_return(IntType)
def _parse_log_level(log_level):
    """
    Parse logging level

    @param   log_level  Logging level (string)
    @return  Logging level (int)
    """
    type_check(log_level, StringType)

    try:
        return {
            "debug":    logging.DEBUG,
            "info":     logging.INFO,
            "warning":  logging.WARNING,
            "error":    logging.ERROR,
            "critical": logging.CRITICAL
        }[log_level.lower()]

    except KeyError:
        raise ParsingError("Invalid logging level")


class MiscConfig(object):
    """ Miscellaneous configuration """
    def __init__(self, log_level):
        """
        Parse miscellaneous configuration

        @param   log_level  Logging level
        """
        type_check(log_level, StringType)

        self._log_level = _parse_log_level(log_level)

    @type_check_return(IntType)
    def log_level(self):
        """
        Get logging level

        @return  Logging level (int)
        """
        return self._log_level
