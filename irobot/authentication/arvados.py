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
from types import BooleanType, NoneType, StringType

from irobot.authentication._base import BaseAuthHandler
from irobot.common import type_check_arguments, type_check_return
from irobot.config.authentication import ArvadosAuthConfig
from irobot.logging import LogWriter


class ArvadosAuthHandler(LogWriter, BaseAuthHandler):
    """ Arvados authentication handler """
    @type_check_arguments(config=ArvadosAuthConfig, logger=(logging.Logger, NoneType))
    def __init__(self, config, logger=None):
        """
        Constructor

        @param   config  Arvados authentication configuration
        @param   logger  Logger
        """
        super(ArvadosAuthHandler, self).__init__(logger=logger)
        self._config = config

        # TODO
    
    @type_check_return(BooleanType)
    @type_check_arguments(auth_header=StringType)
    def validate(self, auth_header):
        """
        Validate the authorisation header

        @param   auth_header  Contents of the "Authorization" header (string)
        @return  Validation success (boolean)
        """

        # TODO
        pass
