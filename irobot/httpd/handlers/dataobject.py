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

import re
import os
from typing import Dict

from aiohttp.web import Request, Response

from irobot.httpd._common import HandlerT
from irobot.httpd._error import error_factory
from irobot.httpd.handlers import _decorators as request


async def _todo(req:Request) -> Response:
    """ Placeholder handler """
    irods_path = req["irobot_irods_path"]
    raise NotImplementedError(f"Watch this space... {irods_path}")


# Method -> Handler delegation table
_delegates:Dict[str, HandlerT] = {
    "GET":    _todo,
    "HEAD":   _todo,
    "POST":   _todo,
    "DELETE": _todo
}


@request.allow("GET", "HEAD", "POST", "DELETE")
async def data_object(req:Request) -> Response:
    """
    Data object handling delegation

    @param   req  Request
    @return  Response
    """
    # Extract path from URL and normalise
    irods_path = os.path.normpath("/" + req.match_info["irods_path"])
    irods_path = re.sub(r"^/+", "/", irods_path)

    # Initial sanity check on iRODS path: We cannot have data objects in
    # the root collection, so we must be at least one level deep
    if not re.match(r".+/.+", irods_path):
        raise error_factory(404, f"No such data object {irods_path}; "
                                  "must be at least one collection deep.")

    req["irobot_irods_path"] = irods_path
    return await _delegates[req.method](req)
