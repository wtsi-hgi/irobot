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
from typing import Dict, Optional, Tuple, Type

from aiohttp import web

from irobot.httpd._common import ENCODING

# Tuple of error reason (string) and error class
_ErrorT = Tuple[str, Type[web.HTTPError]]


def _undefined_error_factory(status: int) -> _ErrorT:
    """
    Fallback error factory

    @param   status  HTTP response status (int)
    @return  Error reason and class
    """
    class _UndefinedError(web.HTTPError):
        """ Undefined HTTP Error """
        status_code = status

    return "Undefined Error", _UndefinedError


# We don't use aiohttp's HTTPMethodNotAllowed because its constructor
# has a different signature to what we expect. Instead we just create a
# simple exception and force upstream to pass in a correct Allow header.
# FIXME? Leaky abstraction
_, _HTTPMethodNotAllowed = _undefined_error_factory(405)


# Error responses which iRobot can return
_status_map: Dict[int, _ErrorT] = {
    401: ("Unauthorized",          web.HTTPUnauthorized),
    403: ("Forbidden",             web.HTTPForbidden),
    404: ("Not Found",             web.HTTPNotFound),
    405: ("Method Not Allowed",    _HTTPMethodNotAllowed),
    406: ("Not Acceptable",        web.HTTPNotAcceptable),
    409: ("Conflict",              web.HTTPConflict),
    416: ("Range Not Satisfiable", web.HTTPRequestRangeNotSatisfiable),
    500: ("Internal Server Error", web.HTTPInternalServerError),
    502: ("Bad Gateway",           web.HTTPBadGateway),
    504: ("Gateway Timeout",       web.HTTPGatewayTimeout),
    507: ("Insufficient Storage",  web.HTTPInsufficientStorage)
}


def error_factory(status: int, description: str, *, headers: Optional[Dict[str, str]]=None) -> web.HTTPError:
    """
    Standardised JSON error response factory

    @param   status       HTTP response status (int)
    @param   description  Human readable error description (string)
    @param   headers      Additional response headers (optional; dictionary)
    @return  HTTP error response (web.HTTPError)
    """
    reason, cls = _status_map.get(status, _undefined_error_factory(status))

    # HTTPException subclasses Response, but its constructor doesn't
    # have a charset argument and setting it in the content_type
    # argument raises an error... Sheesh
    headers_with_content_type = {
        "Content-Type": f"application/json; charset={ENCODING}",
        **(headers or {})
    }

    body = json.dumps({
        "status":      status,
        "reason":      reason,
        "description": description
    }).encode(ENCODING)

    return cls(reason=reason, headers=headers_with_content_type, body=body)
