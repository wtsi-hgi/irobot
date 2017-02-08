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

from logging import Logger
from types import IntType, NoneType, StringType

from irobot.common import type_check_arguments


class LogWriter(object):
    """ Logging base class """
    @type_check_arguments(logger=(NoneType, Logger))
    def __init__(self, logger=None, *args, **kwargs):
        """
        Constructor

        @param   logger  Logging instance
        """
        super(LogWriter, self).__init__(*args, **kwargs)
        self._logger = logger

    @type_check_arguments(level=IntType, message=StringType)
    def log(self, level, message, *args, **kwargs):
        """
        Write to log

        @param   level    Logging level (int)
        @param   message  Log message (string)
        """
        if self._logger:
            self._logger.log(level, message, *args, **kwargs)
