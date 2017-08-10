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
from typing import List, NamedTuple, Optional

from .authentication import BaseAuthHandler, ArvadosAuthHandler, HTTPBasicAuthHandler
from .config import iRobotConfiguration
from .irods import iRODS
from .httpd import start_httpd
from .precache import Precache
from .logging import create_logger


class _BootstrapLoggingConfig(NamedTuple):
    """ Quick-and-dirty LoggingConfig stub """
    output:Optional[str] = None
    level:int = logging.CRITICAL

class _BootstrapLogging(object):
    """ Bootstrap logger """
    def __enter__(self) -> logging.Logger:
        self.logger = create_logger(_BootstrapLoggingConfig())
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type:
            raise exc_val

        self.logger.handlers = []
        del self.logger

        return True


def _instantiate_authentication_handlers(config:iRobotConfiguration, logger:logging.Logger) -> List[BaseAuthHandler]:
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
    with _BootstrapLogging():
        config = iRobotConfiguration(os.environ.get("IROBOT_CONF", "~/irobot.conf"))

    # Plumb everything together and start
    logger = create_logger(config.logging)
    irods = iRODS(config.irods, logger)
    precache = Precache(config.precache, irods, logger)
    auth_handlers = _instantiate_authentication_handlers(config, logger)
    start_httpd(config.httpd, precache, auth_handlers, logger)
