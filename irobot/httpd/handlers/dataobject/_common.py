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

from aiohttp.web import Response

from irobot.precache import AbstractDataObject, InProgress


class ETAResponse(Response, Exception):
    """ ETA response: 202 Accepted with an iRobot-ETA header """
    def __init__(self, progress:InProgress) -> None:
        """
        Constructor

        @param   progress  In progress exception (InProgress)
        """
        eta = str(progress)
        Response.__init__(self, status=202, headers={"iRobot-ETA": eta})
        Exception.__init__(self, eta)


def metadata_has_changed(data_object:AbstractDataObject) -> bool:
    """
    Check whether the cached metadata and the most recent metadata for a
    data object has changed, in terms of its file size, checksum and
    timestamps

    @param   data_object  Data object (AbstractDataObject)
    @return  Changed status (boolean)
    """
    current = data_object.metadata
    new = data_object.refetch_metadata()

    return current.checksum != new.checksum \
        or current.size     != new.size \
        or current.created  != new.created \
        or current.modified != new.modified
