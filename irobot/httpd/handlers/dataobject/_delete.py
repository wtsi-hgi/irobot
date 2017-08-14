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

from aiohttp.web import Request, Response

from irobot.httpd._error import error_factory
from irobot.precache.db import Datatype, Status


async def handler(req:Request) -> Response:
    """ Placeholder handler """
    precache = req.app["irobot_precache"]
    irods_path = req["irobot_irods_path"]

    if irods_path not in precache:
        raise error_factory(404, f"No such data object \"{irods_path}\" "
                                  "in precache; cannot delete.")

    data_object = precache(irods_path)
    if data_object.status[Datatype.data] != Status.ready or data_object.contention:
        raise error_factory(409, f"Data object \"{irods_path}\" is in "
                                  "use; cannot delete.")

    raise NotImplementedError(f"DELETE {irods_path}: Watch this space...")
