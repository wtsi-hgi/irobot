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
from typing import Callable

from aiohttp.web import Request, Response

from irobot.httpd._common import HandlerT
from irobot.httpd._error import error_factory


def allow_request(*methods) -> Callable[[HandlerT], HandlerT]:
    """
    Parametrisable decorator which checks the request method matches
    what's allowed (raising an error, if not) and responds appropriately
    to an OPTIONS request.

    @param   methods  Allowed methods (strings)
    @return  Decorator
    """
    # Allowed methods (obviously OPTIONS is included)
    allowed = {m.upper() for m in [*methods, "OPTIONS"]}
    allow_header = {"Allow": ", ".join(allowed)}

    def _decorator(handler:HandlerT) -> HandlerT:
        """
        Decorator that handles the allowed methods

        @param   handler  Handler function to decorate
        @return  Decorated handler
        """
        @wraps(handler)
        async def _decorated(request:Request) -> Response:
            """
            Check request method against allowed methods

            @param   request  HTTP request (Request)
            @return  HTTP response (Response)
            """
            if request.method not in allowed:
                raise error_factory(405, f"Cannot {request.method} the resource at f{request.url}.", headers=allow_header)

            if request.method == "OPTIONS":
                return Response(status=200, headers=allow_header)

            return await handler(request)

        return _decorated

    return _decorator
