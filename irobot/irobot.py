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
from typing import List

from .authentication import BaseAuthHandler, ArvadosAuthHandler, HTTPBasicAuthHandler
from .config import Configuration
from .config.log import LoggingConfig
from .irods import iRODS
from .httpd import start_httpd
from .precache import Precache
from .logging import create_logger


def _log_config(config:Configuration, logger:logging.Logger) -> None:
    """ Log configuration """
    logger.info("Configuration loaded from %s", config.file)

    for section_name, section in config.get_sections().items():
        logger.info("%s Configuration: %s", section_name, str(section))

    for handler in config.httpd.authentication:
        logger.info("%s Authentication Configuration: %s", handler, str(getattr(config.authentication, handler)))


def _instantiate_authentication_handlers(config:Configuration, logger:logging.Logger) -> List[BaseAuthHandler]:
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
    _bootstrap_logger = create_logger(LoggingConfig("STDERR", "critical"))

    config = Configuration(os.environ.get("IROBOT_CONF", "~/irobot.conf"))

    # Upgrade to configured logging
    _bootstrap_logger.handlers = []
    logger = create_logger(config.logging)
    _log_config(config, logger)

    # Plumb everything together and start
    irods = iRODS(config.irods, logger)
    precache = Precache(config.precache, irods, logger)
    auth_handlers = _instantiate_authentication_handlers(config, logger)
    start_httpd(config.httpd, precache, auth_handlers, logger)
