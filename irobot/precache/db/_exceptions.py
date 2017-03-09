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

class StatusExists(Exception):
    """ Raised when a new status is set that is not unique to that file  """

class SwitchoverExists(Exception):
    """ Raised when a switchover record already exists """

class SwitchoverDoesNotExist(Exception):
    """ Raised when a switchover record doesn't exist """

class PrecacheExists(Exception):
    """ Raised when a precache entity already exists """
