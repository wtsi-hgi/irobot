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

import atexit
import logging
import sys
import time
from types import IntType, NoneType, StringType

from irobot.common import type_check_arguments, type_check_return
from irobot.config.log import LoggingConfig


class LogWriter(object):
    """ Logging base class """
    @type_check_arguments(logger=(NoneType, logging.Logger))
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


@type_check_arguments(logger=logging.Logger)
def _exception_handler(logger):
    """
    Create an exception handler that logs uncaught exceptions (except
    keyboard interrupts) before terminating
    """
    def _log_uncaught_exception(exc_class, exc_obj, traceback):
        if issubclass(exc_class, KeyboardInterrupt):
            sys.__excepthook__(exc_class, exc_obj, traceback)

        else:
            logger.critical(exc_obj.message, exc_info=(exc_class, exc_obj, traceback))
            sys.exit(1)

    return _log_uncaught_exception


@type_check_return(logging.Logger)
@type_check_arguments(config=LoggingConfig)
def create_logger(config):
    """
    Create and configure a logger

    @param   config  Logging configuration
    @return  Logger (logging.Logger)
    """
    formatter = logging.Formatter(
        # Tab-delimited: Timestamp Level Message
        fmt="%(asctime)s\t%(levelname)s\t%(message)s",

        # ISO 8601
        datefmt="%Y-%m-%dT%H:%M:%SZ+00:00"
    )
    formatter.converter = time.gmtime  # Force to UTC

    out = config.output()
    handler = logging.FileHandler(out) if out else logging.StreamHandler()
    atexit.register(handler.close)

    handler.setLevel(config.level())
    handler.setFormatter(formatter)

    logger = logging.getLogger("irobot")
    logger.setLevel(config.level())
    logger.addHandler(handler)

    sys.excepthook = _exception_handler(logger)

    return logger
