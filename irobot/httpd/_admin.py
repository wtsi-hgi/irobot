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

from functools import wraps

from aiohttp.web import Request, Response

from irobot.httpd._allow import allow_request
from irobot.httpd._common import HandlerT
from irobot.httpd._error import error_factory


def _check_admin_request(handler:HandlerT) -> HandlerT:
    """
    Decorator that checks admin requests are appropriate

    @param   handler  Handler function to decorate
    @return  Decorated handler
    """
    @wraps(handler)
    async def _decorated(request:Request) -> Response:
        """
        Check Accept header is OK

        @param   request  HTTP request (Request)
        @return  HTTP response (Response)
        """
        # TODO
        return await handler(request)

    return _decorated


@allow_request("GET", "HEAD")
@_check_admin_request
async def status(request:Request) -> Response:
    """
    Status handler

    @param   request  HTTP request (Request)
    @return  HTTP response (Response)
    """
    raise NotImplementedError("OMG!!")


@allow_request("GET", "HEAD")
@_check_admin_request
async def config(request:Request) -> Response:
    """
    Config status handler

    @note    Is this necessary?...

    @param   request  HTTP request (Request)
    @return  HTTP response (Response)
    """
    raise NotImplementedError("OMG!!")


@allow_request("GET", "HEAD")
@_check_admin_request
async def precache(request:Request) -> Response:
    """
    Precache status handler

    @param   request  HTTP request (Request)
    @return  HTTP response (Response)
    """
    raise NotImplementedError("OMG!!")
