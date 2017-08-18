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

from typing import Dict

from aiohttp.web import Request, Response

from irobot.httpd._common import HandlerT
from irobot.httpd.handlers import _decorators as request


async def data_handler(req:Request) -> Response:
    """ Data handler """
    irods_path = req["irobot_irods_path"]
    raise NotImplementedError(f"I don't know how to get the data for {irods_path}")


async def metadata_handler(req:Request) -> Response:
    """ Metadata handler """
    irods_path = req["irobot_irods_path"]
    raise NotImplementedError(f"I don't know how to get the metadata for {irods_path}")


# Media type -> Handler delegation table
_data = "application/octet-stream"
_metadata = "application/vnd.irobot.metadata+json"

_media_delegates:Dict[str, HandlerT] = {
    "application/octet-stream":             data_handler,
    "application/vnd.irobot.metadata+json": metadata_handler
}

@request.accept(*_media_delegates.keys())
async def handler(req:Request) -> Response:
    """ Delegate GET (and HEAD) requests based on preferred media type """
    preferred = req["irobot_preferred"]
    resp = await _media_delegates[preferred](req)

    if req.method == "HEAD":
        content_length = resp.content_length
        resp.body = None
        resp.headers["Content-Length"] = str(content_length)

    return resp
