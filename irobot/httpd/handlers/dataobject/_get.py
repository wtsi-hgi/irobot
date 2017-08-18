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
from irobot.httpd.handlers.dataobject._common import ETAResponse
from irobot.precache import PrecacheFull, InProgress

# Media types
_data = "application/octet-stream"
_metadata = "application/vnd.irobot.metadata+json"


async def data_handler(req:Request) -> Response:
    """ Data handler """
    irods_path = req["irobot_irods_path"]
    raise NotImplementedError(f"I don't know how to get the data for {irods_path}")


async def metadata_handler(req:Request) -> Response:
    """ Metadata handler """
    data_object = req["irobot_data_object"]
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
    # FIXME This is copied-and-pasted, more-or-less, from the POST
    # handler's module. Move this higher up the call chain...
    try:
        precache = req.app["irobot_precache"]
        irods_path = req["irobot_irods_path"]
        req["irobot_data_object"] = precache(irods_path)

    except InProgress as e:
        # Fetching in progress => 202 Accepted
        # FIXME This shouldn't happen for a metadata request, because
        # the metadata is fetched synchronously...
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

    preferred = req["irobot_preferred"]
    resp = await _media_delegates[preferred](req)

    if req.method == "HEAD":
        content_length = resp.content_length
        resp.body = None
        resp.headers["Content-Length"] = str(content_length)

    return resp
