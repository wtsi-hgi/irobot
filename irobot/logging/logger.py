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
from traceback import print_tb
from types import TracebackType
from typing import Callable, Optional, Type

from irobot.common import ISO8601_UTC
from irobot.config import LoggingConfig


class LogWriter(object):
    """ Logging base class """
    def __init__(self, logger:Optional[logging.Logger] = None, *args, **kwargs) -> None:
        """
        Constructor

        @param   logger  Logging instance
        """
        super().__init__(*args, **kwargs)
        self._logger = logger

    def log(self, level:int, message:str, *args, **kwargs) -> None:
        """
        Write to log

        @param   level    Logging level (int)
        @param   message  Log message (string)
        """
        if self._logger:
            self._logger.log(level, message, *args, **kwargs)


def _exception_handler(logger:logging.Logger) -> Callable:
    """
    Create an exception handler that logs uncaught exceptions (except
    keyboard interrupts) and spews the traceback to stderr (in debugging
    mode) before terminating
    """
    def _log_uncaught_exception(exc_type:Type[BaseException], exc_val:BaseException, traceback:TracebackType) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_val, traceback)

        else:
            logger.critical(str(exc_val) or exc_type.__name__)
            if __debug__:
                print_tb(traceback)

            sys.exit(1)

    return _log_uncaught_exception


def create_logger(config:LoggingConfig) -> logging.Logger:
    """
    Create and configure a logger

    @param   config  Logging configuration
    @return  Logger (logging.Logger)
    """
    formatter = logging.Formatter(
        # Tab-delimited: Timestamp Level Message
        fmt="%(asctime)s\t%(levelname)s\t%(message)s",

        # ISO8601 assumed UTC
        datefmt=ISO8601_UTC
    )
    formatter.converter = time.gmtime  # Force to UTC

    out = config.output
    handler = logging.FileHandler(out) if out else logging.StreamHandler()
    atexit.register(handler.close)

    handler.setLevel(config.level)
    handler.setFormatter(formatter)

    logger = logging.getLogger("irobot")
    logger.setLevel(config.level)
    logger.addHandler(handler)

    sys.excepthook = _exception_handler(logger)

    return logger
