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

from datetime import datetime

from aiohttp.web import Response

from irobot.common import ISO8601_UTC
from irobot.precache import AbstractDataObject, InProgress


class ETAResponse(Response):
    """ ETA response: 202 Accepted with an iRobot-ETA header """
    def __init__(self, exc:InProgress) -> None:
        """
        Constructor

        @param   exc  In progress exception (InProgress)
        """
        eta, stderr = exc.eta
        headers = {"iRobot-ETA": datetime.strftime(eta, ISO8601_UTC) + f" +/- {stderr}"}
        super().__init__(status=202, headers=headers)


def metadata_has_changed(data_object:AbstractDataObject) -> bool:
    """
    Check whether the cached metadata and the most recent metadata for a
    data object has changed, in terms of its file size, checksum and
    timestamps

    @param   data_object  Data object (AbstractDataObject)
    @return  Changed status (boolean)
    """
    # TODO
    pass
