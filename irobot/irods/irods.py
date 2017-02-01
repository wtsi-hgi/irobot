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

from types import StringType

from irobot.common import type_check
from irobot.config.irods import iRODSConfig


class iRODS(object):
    """ High level iRODS interface """
    def __init__(self, irods_config):
        """
        Constructor

        @param   irods_config  iRODS configuration
        """
        type_check(irods_config, iRODSConfig)

    def get_dataobject(self, irods_path, local_path):
        """
        Retrieve data object from iRODS and store it in the local
        filesystem

        @param   irods_path  Path to data object on iRODS (string)
        @param   local_path  Local filesystem target file (string)
        """
        type_check(irods_path, StringType)
        type_check(local_path, StringType)

    def get_metadata(self, irods_path):
        """
        Retrieve AVU and filesystem metadata for data object from iRODS

        @param   irods_path  Path to data object on iRODS (string)
        @return  AVU and filesystem metadata (tuple of dictionaries)
        @note    AVUs will have their units stripped off
        """
        type_check(irods_path, StringType)
