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

from irobot.httpd.handlers.dataobject._common import get_data_object, metadata_has_changed


async def handler(req: Request) -> Response:
    """ (Re)fetch data object from iRODS if it is not contended """
    precache = req.app["irobot_precache"]
    irods_path = req["irobot_irods_path"]
    data_object = get_data_object(precache, irods_path, raise_inprogress=True, raise_inflight=True)

    # Delete and refetch if needs be
    if metadata_has_changed(data_object):
        data_object.delete()
        return await handler(req)

    # If nothing needs to be done, then fallback to an empty 201 Created
    # (which isn't technically true, necessarily, but it's close enough)
    return Response(status=201)
