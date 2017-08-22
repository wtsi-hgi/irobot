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
from typing import Dict, List, Tuple

from aiohttp.web import Request, Response

from irobot.irods import MetadataJSONEncoder
from irobot.httpd._common import ENCODING, HandlerT
from irobot.httpd._error import error_factory
from irobot.httpd.handlers import _decorators as request
from irobot.httpd.handlers.dataobject._common import get_data_object

# Media types
_data = "application/octet-stream"
_metadata = "application/vnd.irobot.metadata+json"


_RE_RANGE_REQ = re.compile(r"""
    ^
    (?P<units> \w+ )
    =
    (?P<ranges> \d* - \d* (?: , \d* - \d* )* )
    $
""", re.IGNORECASE | re.VERBOSE)

_RE_RANGE = re.compile(r"""
    (?= .* \d )        # Must contain at least one number
    ^
    (?P<from> \d+ )?   # Range from
    -
    (?P<to> \d+ )?     # Range to
    $
""", re.VERBOSE)

def _parse_range(range_header:str, filesize:int) -> List[Tuple[int, int]]:
    """
    Parse and canonicalise the required byte range, raising a 416
    Range Not Satisfiable error if the requested range is invalid in
    any way.

    @param   range_header  Value of the range request header (string)
    @param   filesize      File size (int)
    @return  Ordered list of ranges, merged if overlapping (list)
    """
    req = _RE_RANGE_REQ.match(range_header)
    ranges = []

    if not req:
        raise error_factory(416, "Could not parse range request")

    if req["units"].lower() != "bytes":
        unit = req["units"]
        raise error_factory(416, "Can only respond with byte ranges; "
                                 f"\"{unit}\" is not an understood unit.")

    # Parse the ranges
    for r in req["ranges"].split(","):
        range_match = _RE_RANGE.match(r)
        invalid_range = error_factory(416, f"Invalid range \"{r}\".")

        if not range_match:
            raise invalid_range

        range_from = range_match["from"]
        range_to   = range_match["to"]

        # Three cases:
        # a-b  Range from a to b, inclusive, where a <= b
        # a-   Range from a to end, inclusive
        # -b   Range from end to end -b, inclusive

        if range_from:
            range_from = int(range_from)
            range_to   = int(range_to) if range_to else filesize
        else:
            range_from = filesize - int(range_to)
            range_to   = filesize

        if range_from > range_to or range_from > filesize:
            raise invalid_range

        ranges.append((range_from, range_to))

    ranges = sorted(ranges)
    merged_ranges = []

    # Merge overlapping ranges
    new_range = None
    for r in ranges:
        if not new_range:
            new_range = r

        last_from, last_to = new_range
        this_from, this_to = r

        if last_to >= this_from - 1:
            new_range = (last_from, this_to)
        else:
            merged_ranges.append(new_range)
            new_range = r

    merged_ranges.append(new_range)

    return merged_ranges


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
    data_object.update_last_access()

    # TODO Reset contention after all file operations have completed

    raise NotImplementedError(f"I don't know how to get the data for {irods_path}")


async def metadata_handler(req:Request) -> Response:
    """ Metadata handler """
    data_object = get_data_object(req, raise_inprogress=False, raise_inflight=False)
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
