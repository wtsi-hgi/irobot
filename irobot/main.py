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
import os
from types import TracebackType
from typing import List, Type, overload

from irobot import __version__
from irobot.authentication import BaseAuthHandler, ArvadosAuthHandler, HTTPBasicAuthHandler
from irobot.config import iRobotConfiguration, LoggingConfig
from irobot.httpd import start_httpd
from irobot.irods import Irods
from irobot.logs import create_logger
from irobot.precache import Precache


class _BootstrapLogging(object):
    """ Bootstrap logger """
    logger: logging.Logger
    config: LoggingConfig

    def __init__(self) -> None:
        # This is a bit of a hack, but never mind :P
        from configparser import ConfigParser
        from irobot.config import config

        bootstrap_config = ConfigParser()
        bootstrap_config.read_string("""
            [logging]
            output = STDERR
            level = info
        """)

        self.config = config._factories("logging", bootstrap_config)

    def __enter__(self) -> logging.Logger:
        self.logger = create_logger(self.config)
        return self.logger

    @overload
    def __exit__(self, exc_type: Type[BaseException], exc_val: BaseException, exc_tb: TracebackType) -> bool: ...

    def __exit__(self, exc_type: None, exc_val: None, exc_tb: None) -> bool:
        if exc_type:
            # Propagate exception
            return False

        self.logger.handlers = []
        del self.logger
        return True


def _instantiate_authentication_handlers(config: iRobotConfiguration, logger: logging.Logger) -> List[BaseAuthHandler]:
    """ Instantiate authentication handlers """
    handler_mapping = {
        "arvados": ArvadosAuthHandler,
        "basic": HTTPBasicAuthHandler
    }

    return [
        handler_mapping[handler](getattr(config.authentication, handler), logger)
        for handler in config.httpd.authentication
    ]


if __name__ == "__main__":
    # For the sake of homogeneity, create a logger and exception handler
    # for bootstrapping the configuration parsing
    with _BootstrapLogging() as bootstrap_logger:
        bootstrap_logger.info(f"Starting iRobot {__version__}")
        config = iRobotConfiguration(os.environ.get("IROBOT_CONF", "~/irobot.conf"))

    # Plumb everything together and start
    logger = create_logger(config.logging)
    irods = Irods(config.irods, logger)
    precache = Precache(config.precache, irods, logger)
    auth_handlers = _instantiate_authentication_handlers(config, logger)
    start_httpd(config.httpd, precache, auth_handlers, logger)
