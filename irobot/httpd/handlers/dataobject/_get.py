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

from aiohttp.multipart import MultipartWriter
from aiohttp.web import Request, Response, StreamResponse

from irobot.irods import MetadataJSONEncoder
from irobot.httpd._common import ENCODING, HandlerT
from irobot.httpd.handlers import _decorators as request
from irobot.httpd.handlers.dataobject._common import get_data_object
from irobot.httpd.handlers.dataobject._range_parser import canonicalise_ranges, parse_range


# Media types
_data      = "application/octet-stream"
_metadata  = "application/vnd.irobot.metadata+json"
_multipart = "multipart/bytes"


async def data_handler(req:Request) -> StreamResponse:
    """ Data handler """
    precache = req["irobot_precache"]
    irods_path = req["irobot_irods_path"]
    data_object = get_data_object(precache, irods_path, raise_inprogress=True, raise_inflight=False)

    # If we've got this far, then we can return actual data!

    # TODO If we want to return a range, then it would be possible to do
    # so while data is being fetched, provided that range has already
    # been accounted for. Our iRODS interface doesn't track this, so for
    # now we just have this simple can we/can't we distinction on the
    # basis of the complete data...

    if req.headers.get("If-None-Match") == data_object.metadata.checksum:
        # Client's version matches, so there's nothing to do
        return Response(status=304)

    data_object.update_last_access()
    headers = {"ETag": data_object.metadata.checksum}

    is_range_request = "Range" in req.headers

    # Steam out the data
    with data_object as do_file:
        status_code = 202 if is_range_request else 200
        content_type = _multipart if is_range_request else _data
        headers = {**headers, "Content-Type": content_type}

        resp = StreamResponse(status=status_code, headers=headers)
        resp.enable_chunked_encoding()
        resp.enable_compression()

        await resp.prepare(request)

        if is_range_request:
            # Fetch ranges from header and mix with checksums, if they exist
            _ranges = parse_range(req.headers["Range"], data_object.metadata.size)
            _checksummed_ranges = map(data_object.checksums, _ranges)
            ranges = canonicalise_ranges(_ranges, *_checksummed_ranges)

            multipart_writer = MultipartWriter("bytes")
            for r in ranges:
                range_header = {
                    "Content-Type": _data,
                    **({"Content-MD5": r.checksum} if r.checksum else {})
                }

                do_file.seek(r.start)
                range_size = (r.finish - r.start) + 1
                multipart_writer.append(do_file.read(range_size), range_header)

                # TODO? Write to response??

        else:
            while True:
                # TODO Get the chunking size from, e.g., environment
                data = do_file.read(8192)
                if not data:
                    await resp.drain()
                    break

                resp.write(data)

        return resp


async def metadata_handler(req:Request) -> Response:
    """ Metadata handler """
    precache = req["irobot_precache"]
    irods_path = req["irobot_irods_path"]
    data_object = get_data_object(precache, irods_path, raise_inprogress=False, raise_inflight=False)

    data_object.update_last_access()
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

    # We allow byte range requests, so let the client know
    resp.headers["Accept-Ranges"] = "bytes"

    if req.method == "HEAD":
        # It seems like this should be easier...
        content_length = resp.content_length
        resp.body = None
        resp.headers["Content-Length"] = str(content_length)

    return resp
