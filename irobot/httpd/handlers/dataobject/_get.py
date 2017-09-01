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
from typing import Dict, Generator, List, Optional

from aiohttp.web import Request, Response, StreamResponse

from irobot.common import ByteRange
from irobot.irods import MetadataJSONEncoder
from irobot.httpd._common import ENCODING, HandlerT
from irobot.httpd.handlers import _decorators as request
from irobot.httpd.handlers.dataobject._common import get_data_object
from irobot.httpd.handlers.dataobject._range_parser import canonicalise_ranges, parse_range
from irobot.precache import AbstractDataObject


# Media types
_DATA      = "application/octet-stream"
_METADATA  = "application/vnd.irobot.metadata+json"
_MULTIPART = "multipart/byteranges"


# Multipart bits and pieces
_CRLF = b"\r\n"
_RE_BOUNDARY = re.compile(r"(?!.* $)^[a-zA-Z0-9'()+_,./:=? -]{1,70}$")


_DataGenerator = Generator[bytes, None, None]

class _DataObjectResponseWriter(object):
    """ Data Object data response writer """
    _data_object:AbstractDataObject

    def __init__(self, data_object:AbstractDataObject) -> None:
        """
        Constructor

        @param   data_object  Data object (AbstractDataObject)
        """
        self.data_object = data_object

    def _content_range(self, byte_range:ByteRange) -> str:
        """
        Create Content-Range string

        @param   byte_range  Byte Range (ByteRange)
        @return  Value for Content-Range response header (string)
        """
        return f"bytes {byte_range.start}-{byte_range.finish + 1}/{self._data_object.metadata.size}"

    def _generate_boundary(self, ranges:List[ByteRange]) -> str:
        """
        Generate a unique boundary (i.e., when prefixed with "--", its
        ASCII encoding doesn't clash with any of the data starting at
        the specified byte ranges

        @param   ranges    Byte ranges (list of ByteRange)
        @return  Multipart boundary (string)
        """
        # TODO
        assert ranges
        return "ABC123"

    def _get_data(self, byte_range:Optional[ByteRange] = None, *, chunk_size:int = 8192) -> _DataGenerator:
        """
        Get data or range of data from data object

        @param   byte_range  Byte range (ByteRange; None for everything, default)
        @param   chunk_size  Chunk size (default 8KB)
        @return  Generator that yields the requested data (bytes)
        """
        # FIXME Don't open the file descriptor in this generator as it
        # controls the data object contention. In the range writer,
        # multiple generators will be used (one per range), so the data
        # object will go in and out of contention, which puts it in a
        # position where it could be deleted while streaming...which is
        # exactly what we want to avoid!
        assert chunk_size > 0

        if byte_range:
            start, finish, _ = byte_range
            assert 0 <= start < finish
            to_consume = finish - start
            consumed = 0

        else:
            start = 0

        with self.data_object as fd:
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

    def _write_multipart(self, ranges:List[ByteRange], *, boundary:str) -> _DataGenerator:
        """
        Write multipart payload, per RFC7233
        https://tools.ietf.org/html/rfc7233#appendix-A

        @param   ranges    Byte ranges (list of ByteRange)
        @param   boundary  Multipart boundary (string)
        @return  Generator that yields the multipart response body (bytes)
        """
        # TODO
        pass

    async def write(self, req:Request) -> StreamResponse:
        """
        Create response containing the appropriate payload

        @param   req   Request
        @return  Data object response
        """
        data_generator:_DataGenerator
        ranges:List[ByteRange] = []
        headers:Dict[str, str] = {}

        # The entity tag is the MD5 checksum (per iRODS) of the entire
        # data object, unless a single range, which has a calculated
        # checksum, is requested. In which case, that range's checksum
        # is used.
        # FIXME? Is this reasonable behaviour?...
        etag = self._data_object.metadata.checksum

        if "Range" in req.headers:
            # Fetch ranges from header and mix with checksums, if they exist
            _ranges = parse_range(req.headers["Range"], self._data_object.metadata.size)
            _checksummed_ranges = map(self._data_object.checksums, _ranges)
            ranges = canonicalise_ranges(_ranges, *_checksummed_ranges)

        if ranges:
            # Responding with partial content
            status_code = 206

            head_range, *tail_ranges = ranges
            if tail_ranges:
                # Multipart response
                boundary = self._generate_boundary(ranges)
                content_type = f"{_MULTIPART}; boundary=\"{boundary}\""

                data_generator = self._write_multipart(ranges, boundary=boundary)

            else:
                # If there's only one range, then we don't use multipart
                content_type = _DATA
                etag = head_range.checksum or etag
                headers["Content-Range"] = self._content_range(head_range)

                data_generator = self._get_data(head_range)

        else:
            # Respond with all content
            status_code = 200
            content_type = _DATA

            data_generator = self._get_data()

        headers["ETag"] = etag
        headers["Content-Type"] = content_type

        resp = StreamResponse(status=status_code, headers=headers)
        resp.enable_chunked_encoding()
        resp.enable_compression()
        await resp.prepare(req)

        for data in data_generator:
            resp.write(data)

        await resp.drain()
        return resp


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
    do_response = _DataObjectResponseWriter(data_object)
    return await do_response.write(req)


async def metadata_handler(req:Request) -> Response:
    """ Metadata handler """
    precache = req["irobot_precache"]
    irods_path = req["irobot_irods_path"]
    data_object = get_data_object(precache, irods_path, raise_inprogress=False, raise_inflight=False)

    data_object.update_last_access()
    body = json.dumps(data_object.metadata, cls=MetadataJSONEncoder).encode(ENCODING)
    return Response(status=200, body=body, content_type=_METADATA, charset=ENCODING)


# Media type -> Handler delegation table
_media_delegates:Dict[str, HandlerT] = {
    _DATA:     data_handler,
    _METADATA: metadata_handler
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
