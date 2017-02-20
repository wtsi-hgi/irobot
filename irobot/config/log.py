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
from configparser import ParsingError
from typing import Optional

import irobot.common.canon as canon
from irobot.config._base import BaseConfig


def _canon_output(output:str) -> Optional[str]:
    """
    Canonicalise logging output destination

    @param   output  Logging destination
    """
    if output == "STDERR":
        return None

    return canon.path(output)


def _canon_level(level:str) -> int:
    """
    Canonicalise logging level

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


class LoggingConfig(BaseConfig):
    """ Logging configuration """
    def __init__(self, output:str, level:str) -> None:
        """
        Parse logging configuration

        @param   output  Logging destination
        @param   level   Logging level
        """
        self._output = _canon_output(output)
        self._level = _canon_level(level)

    def __str__(self) -> None:
        return str({
            "output": self._output or "stderr",
            "level": ["debug", "info", "warning", "error", "critical"][(self._level // 10) - 1]
        }).replace("'", "")

    def output(self) -> Optional[str]:
        """
        Get logging output destination

        @return  Logging destination (string or None for stderr)
        """
        return self._output

    def level(self) -> int:
        """
        Get logging level

        @return  Logging level (int)
        """
        return self._level
