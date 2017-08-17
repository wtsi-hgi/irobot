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

from irobot.common import AsyncTaskStatus, DataObjectState
from irobot.httpd._error import error_factory
from irobot.httpd.handlers.dataobject._common import ETAResponse, metadata_has_changed
from irobot.precache import AbstractPrecache, PrecacheFull, InProgress


def _seed_data_object(precache:AbstractPrecache, irods_path:str) -> Response:
    """
    Seed data object; factored out from the request handler so it can be
    more easily called recursively

    @param   precache    Precache (AbstractPrecache)
    @param   irods_path  iRODS data object path (string)
    @return  POST response (Response)
    """
    if irods_path not in precache:
        try:
            # This call will begin the data seeding and almost certainly
            # raise an exception to communicate its status
            _data_object = precache(irods_path)

        except InProgress as e:
            # Fetching in progress => 202 Accepted
            return ETAResponse(e)

        except FileNotFoundError as e:
            # File not found on iRODS => 404 Not Found
            raise error_factory(404, str(e))

        except PermissionError as e:
            # Couldn't access file on iRODS => 403 Forbidden
            raise error_factory(403, str(e))

        except IOError as e:
            # Some other iRODS IO error => 502 Bad Gateway
            raise error_factory(502, str(e))

        except PrecacheFull as e:
            # Precache full => 507 Insufficient Storage
            raise error_factory(507, f"Cannot fetch \"{irods_path}\"; "
                                      "precache is full.")

        # This could happen if the fetching operation completes *really*
        # quickly, but it's unlikely. Either way, just return an empty
        # 201 Created response
        return Response(status=201)

    data_object = precache(irods_path)
    if data_object.status[DataObjectState.data] != AsyncTaskStatus.finished or data_object.contention:
        raise error_factory(409, f"Data object \"{irods_path}\" is "
                                  "inflight or contended; cannot delete.")

    # Delete and refetch if needs be
    if metadata_has_changed(data_object):
        data_object.delete()
        return _seed_data_object(precache, irods_path)

    # If nothing needs to be done, then fallback to an empty 201 Created
    # (which isn't technically true, but it's close enough)
    return Response(status=201)


async def handler(req:Request) -> Response:
    """ (Re)fetch data object from iRODS if it is not contended """
    precache = req.app["irobot_precache"]
    irods_path = req["irobot_irods_path"]

    return _seed_data_object(precache, irods_path)
