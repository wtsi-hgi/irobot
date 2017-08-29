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
from typing import Dict, Generator, IO, Optional

from aiohttp.multipart import MultipartWriter
from aiohttp.web import Request, Response, StreamResponse

from irobot.common import ByteRange
from irobot.irods import MetadataJSONEncoder
from irobot.httpd._common import ENCODING, HandlerT
from irobot.httpd.handlers import _decorators as request
from irobot.httpd.handlers.dataobject._common import get_data_object
from irobot.httpd.handlers.dataobject._range_parser import canonicalise_ranges, parse_range


# Media types
_data      = "application/octet-stream"
_metadata  = "application/vnd.irobot.metadata+json"
_multipart = "multipart/bytes"


# TODO Get default chunk size from, e.g., environment
def _get_data(fd:IO[bytes], *, byte_range:Optional[ByteRange] = None, chunk_size:int = 8192) -> Generator[bytes, None, None]:
    """
    @param   fd          File descriptor
    @param   byte_range  Byte range (ByteRange; None for everything, default)
    @param   chunk_size  Chunk size (default 8KB)
    @return  Generator that yields the requested data (bytes)
    """
    assert chunk_size > 0

    if byte_range:
        start, finish, _ = byte_range
        assert 0 <= start < finish
        to_consume = finish - start
        consumed = 0

    else:
        start = 0

    fd.seek(start)
    to_read = chunk_size

    while True:
        if byte_range:
            if consumed >= to_consume:
                break

            to_read = min(chunk_size, to_consume - consumed)
            consumed += to_read

        data = fd.read(to_read)
        if not data:
            break

        yield data


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
        if is_range_request:
            status_code = 202
            content_type = _multipart
        else:
            status_code = 200
            content_type = _data

        headers = {**headers, "Content-Type": content_type}

        resp = StreamResponse(status=status_code, headers=headers)
        resp.enable_chunked_encoding()
        resp.enable_compression()

        await resp.prepare(req)

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

                data = b""
                for chunk in _get_data(do_file, byte_range=r):
                    data += chunk

                multipart_writer.append(data, range_header)

                # TODO? Write to response??

        else:
            for data in _get_data(do_file):
                resp.write(data)

            await resp.drain()

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
