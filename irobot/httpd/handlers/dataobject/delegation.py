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

import os
import re
from typing import Dict

from aiohttp.web import Request, Response

from irobot.httpd._common import HandlerT
from irobot.httpd._error import error_factory
from irobot.httpd.handlers import _decorators as request
from irobot.httpd.handlers.dataobject._delete import handler as delete_handler
from irobot.httpd.handlers.dataobject._get import handler as get_handler
from irobot.httpd.handlers.dataobject._post import handler as post_handler

# Method -> Handler delegation table
_delegates: Dict[str, HandlerT] = {
    "GET":    get_handler,
    "HEAD":   get_handler,
    "POST":   post_handler,
    "DELETE": delete_handler
}


@request.allow("GET", "HEAD", "POST", "DELETE")
async def data_object(req: Request) -> Response:
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
        raise error_factory(404, f"No such data object \"{irods_path}\"; "
                                 "must be at least one collection deep.")

    req["irobot_irods_path"] = irods_path
    return await _delegates[req.method](req)
