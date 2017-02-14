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

import os

from .config import Configuration
from .logging import create_logger
from .irods import iRODS


def _log_config(logger, config):
    """ Log configuration """
    logger.info("Configuration loaded from %s", config.file)

    for section_name, section in config.get_sections().items():
        logger.info("%s = %s", section_name, str(section))

    for handler in config.httpd.authentication():
        logger.info("%s Authentication = %s", handler, str(getattr(config.authentication, handler)))


if __name__ == "__main__":
    config = Configuration(os.environ.get("IROBOT_CONF", "~/irobot.conf"))
    logger = create_logger(config.logging)

    _log_config(logger, config)

    irods = iRODS(config.irods, logger)

    # TODO Plumb in the precache and HTTP server, when they're ready
