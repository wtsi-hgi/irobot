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

import json
from typing import Dict

from aiohttp.web import Request, Response

from irobot.irods import MetadataJSONEncoder
from irobot.httpd._common import ENCODING, HandlerT
from irobot.httpd.handlers import _decorators as request
from irobot.httpd.handlers.dataobject._common import get_data_object

# Media types
_data = "application/octet-stream"
_metadata = "application/vnd.irobot.metadata+json"


async def data_handler(req:Request) -> Response:
    """ Data handler """
    data_object = get_data_object(req, raise_inprogress=True, raise_inflight=False)

    # If we've got this far, then we can return actual data!

    # TODO If we want to return a range, then it would be possible to do
    # so while data is being fetched, provided that range has already
    # been accounted for. Our iRODS interface doesn't track this, so for
    # now we just have this simple can we/can't we distinction on the
    # basis of the complete data...

    irods_path = req["irobot_irods_path"]
    req.app["irobot_data_object_contention"][irods_path] += 1

    # TODO Reset contention after all file operations have completed

    raise NotImplementedError(f"I don't know how to get the data for {irods_path}")


async def metadata_handler(req:Request) -> Response:
    """ Metadata handler """
    data_object = get_data_object(req, raise_inprogress=False, raise_inflight=False)
    body = json.dumps(data_object.metadata, cls=MetadataJSONEncoder).encode(ENCODING)
    return Response(status=200, body=body, content_type=_metadata, charset=ENCODING)


# Media type -> Handler delegation table
_media_delegates:Dict[str, HandlerT] = {
    _data:     data_handler,
    _metadata: metadata_handler
}

@request.accept(*_media_delegates.keys())
async def handler(req:Request) -> Response:
    """ Delegate GET (and HEAD) requests based on preferred media type """
    preferred = req["irobot_preferred"]
    resp = await _media_delegates[preferred](req)

    if req.method == "HEAD":
        # It seems like this should be easier...
        content_length = resp.content_length
        resp.body = None
        resp.headers["Content-Length"] = str(content_length)

    return resp
