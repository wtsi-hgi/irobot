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
from irobot.precache import AbstractDataObject, InProgress, PrecacheFull


class ETAResponse(Response, Exception):
    """ ETA response: 202 Accepted with an iRobot-ETA header """
    def __init__(self, progress:InProgress) -> None:
        """
        Constructor: Convert an InProgress exception into an ETAResponse

        @param   progress  In progress exception (InProgress)
        """
        eta = str(progress)
        Response.__init__(self, status=202, headers={"iRobot-ETA": eta})
        Exception.__init__(self, eta)


def get_data_object(req:Request, *, raise_inprogress:bool = False, raise_inflight:bool = False) -> AbstractDataObject:
    """
    Get a reference to the data object in the precache, initialising the
    data seeding if the data object is not already in the precache. On
    initial fetch, the precache will almost certainly raise an
    exception, which will be caught and converted to the appropriate
    response, to be handled upstream.

    @note    We have to pass in the entire request, to get access to the
             data object contention table. It's not pretty :P

    @param   req               The HTTP request (Request)
    @param   raise_inprogress  Raise if data object fetching is in progress (bool; default False)
    @param   raise_inflight    Check if the data object is inflight or contended (bool; default False)
    @return  Data object active record (AbstractDataObject)
    """
    # Get the app and request local data
    precache = req.app["irobot_precache"]
    irods_path = req["irobot_irods_path"]
    contention = req.app["irobot_data_object_contention"][irods_path]

    try:
        data_object = precache(irods_path)

    except InProgress as e:
        # Fetching in progress => 202 Accepted
        if raise_inprogress:
            raise ETAResponse(e)

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

    if raise_inflight:
        if contention or data_object.status[DataObjectState.data] != AsyncTaskStatus.finished:
            raise error_factory(409, f"Data object \"{irods_path}\" is "
                                      "inflight or contended; cannot fulfil request.")

    return data_object


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
