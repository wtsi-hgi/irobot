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
from irobot.config._tree_builder import Configuration


def output(value: str) -> Optional[str]:
    """
    Canonicalise logging output destination

    @param   value  Logging destination
    """
    if value == "STDERR":
        return None

    return canon.path(value)


def level(value: str) -> int:
    """
    Canonicalise logging level

    @param   value  Logging level (string)
    @return  Logging level (int)
    """
    try:
        return {
            "debug":    logging.DEBUG,
            "info":     logging.INFO,
            "warning":  logging.WARNING,
            "error":    logging.ERROR,
            "critical": logging.CRITICAL
        }[value.lower()]

    except KeyError:
        raise ParsingError("Invalid logging level")


class LoggingConfig(Configuration):
    """ Logging configuration stub """
