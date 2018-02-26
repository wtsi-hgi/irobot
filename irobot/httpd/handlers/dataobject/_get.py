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
import re
import string
from random import choice
from typing import Dict, Generator, IO, List, Optional

from aiohttp.web import Request, Response, StreamResponse

from irobot.common import ByteRange
from irobot.httpd._common import ENCODING, HandlerT
from irobot.httpd.handlers import _decorators as request
from irobot.httpd.handlers.dataobject._common import get_data_object
from irobot.httpd.handlers.dataobject._range_parser import canonicalise_ranges, parse_range
from irobot.irods import MetadataJSONEncoder
from irobot.precache import AbstractDataObject

# Media types
_DATA = "application/octet-stream"
_METADATA = "application/vnd.irobot.metadata+json"
_MULTIPART = "multipart/byteranges"

# Multipart bits and pieces
_CRLF = b"\r\n"
_DASH = "--".encode("ascii")
_BOUNDARY_CHARS = string.ascii_letters + string.digits + "'()+_,./:=? -"
_RE_BOUNDARY = re.compile(rf"(?!.* $)^[{_BOUNDARY_CHARS}]{{1,70}}$")

_DataGenerator = Generator[bytes, None, None]


def _get_data(fd: IO[bytes], byte_range: Optional[ByteRange]=None, *, chunk_size: int=8192) -> _DataGenerator:
    """
    Get data or range of data from a file descriptor

    @param   fd          File descriptor (IO[bytes])
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


class _DataObjectResponseWriter(object):
    """ Data Object data response writer """
    _data_object: AbstractDataObject

    def __init__(self, data_object: AbstractDataObject) -> None:
        """
        Constructor

        @param   data_object  Data object (AbstractDataObject)
        """
        self.data_object = data_object

    def _content_range(self, byte_range: ByteRange) -> str:
        """
        Create Content-Range string

        @param   byte_range  Byte Range (ByteRange)
        @return  Value for Content-Range response header (string)
        """
        return f"bytes {byte_range.start}-{byte_range.finish + 1}/{self._data_object.metadata.size}"

    def _generate_boundary(self, ranges: List[ByteRange], *, length: int=70) -> str:
        """
        Generate a unique boundary (i.e., when prefixed with "--", its
        ASCII encoding doesn't clash with any of the data starting at
        the specified byte ranges)

        @param   ranges    Byte ranges (list of ByteRange)
        @param   length    Boundary length (int, between 1 and 70; default 70)
        @return  Multipart boundary (string)
        """
        assert ranges
        assert 0 < length <= 70

        taken_boundaries: List[str] = []

        with self._data_object as fd:
            # Check up to the first 72 bytes of each range for potential
            # boundary strings for us to avoid
            for r in ranges:
                prefix_range = ByteRange(r.start, min(r.start + 72, r.finish))

                prefix = b""
                for data in _get_data(fd, prefix_range):
                    prefix += data

                if len(prefix) > 2:
                    prefix_head = prefix[0:2].decode("ascii")
                    prefix_tail = prefix[2:].decode("ascii")

                    if prefix_head == _DASH and _RE_BOUNDARY.match(prefix_tail):
                        taken_boundaries.append(prefix_tail)

        while True:
            boundary = "".join(choice(_BOUNDARY_CHARS) for _ in range(length))

            if _RE_BOUNDARY.match(boundary) and boundary not in taken_boundaries:
                break

        return boundary

    def _write_all(self, byte_range: Optional[ByteRange]=None) -> _DataGenerator:
        """
        Generate data/data range payload

        @param   ranges    Byte ranges (list of ByteRange)
        @return  Generator that yields the full response body (bytes)
        """
        with self._data_object as fd:
            for data in _get_data(fd, byte_range):
                yield data

    def _write_multipart(self, ranges: List[ByteRange], *, boundary: str) -> _DataGenerator:
        """
        Generate multipart payload, per RFC7233 and RFC2046
        * https://tools.ietf.org/html/rfc7233#appendix-A
        * https://tools.ietf.org/html/rfc2046#section-5.1

        @param   ranges    Byte ranges (list of ByteRange)
        @param   boundary  Multipart boundary (string)
        @return  Generator that yields the multipart response body (bytes)
        """
        assert ranges
        assert _RE_BOUNDARY.match(boundary)

        dash_boundary = f"--{boundary}".encode("ascii")
        transport_padding = b""

        with self._data_object as fd:
            for r in ranges:
                yield _CRLF
                yield dash_boundary
                yield transport_padding
                yield _CRLF

                headers = {
                    "Content-Type": _DATA,
                    "Content-Range": self._content_range(r),
                }

                if r.checksum:
                    headers["ETag"] = r.checksum

                # Yield range headers
                yield _CRLF.join(f"{k}: {v}".encode("ascii") for k, v in headers.items())
                yield _CRLF

                # Yield range data
                for data in _get_data(fd, r):
                    yield data

            yield _CRLF
            yield dash_boundary
            yield _DASH
            yield transport_padding

    async def write(self, req: Request) -> StreamResponse:
        """
        Create response containing the appropriate payload

        @param   req   Request
        @return  Data object response
        """
        data_generator: _DataGenerator
        ranges: List[ByteRange] = []
        headers: Dict[str, str] = {}

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

                data_generator = self._write_all(head_range)

        else:
            # Respond with all content
            status_code = 200
            content_type = _DATA

            data_generator = self._write_all()

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


async def data_handler(req: Request) -> StreamResponse:
    """ Data handler """
    precache = req.app["irobot_precache"]
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

    # FIXME Technically, the data object should be marked as contended
    # here and the contention released after the function has completed.
    # Currently, this is instead done within the response writing class,
    # so may be subject to data races from intervening async requests.

    data_object.update_last_access()
    do_response = _DataObjectResponseWriter(data_object)
    return await do_response.write(req)


async def metadata_handler(req: Request) -> Response:
    """ Metadata handler """
    precache = req.app["irobot_precache"]
    irods_path = req["irobot_irods_path"]
    data_object = get_data_object(precache, irods_path, raise_inprogress=False, raise_inflight=False)

    data_object.update_last_access()
    body = json.dumps(data_object.metadata, cls=MetadataJSONEncoder).encode(ENCODING)
    return Response(status=200, body=body, content_type=_METADATA, charset=ENCODING)


# Media type -> Handler delegation table
_media_delegates: Dict[str, HandlerT] = {
    _DATA: data_handler,
    _METADATA: metadata_handler
}


@request.accept(*_media_delegates.keys())
async def handler(req: Request) -> Response:
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
