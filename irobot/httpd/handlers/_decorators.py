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
from irobot.httpd.handlers._accept_parser import RE_MEDIA_TYPE, AcceptParser


_HandlerDecoratorT = Callable[[HandlerT], HandlerT]


def allow(*methods) -> _HandlerDecoratorT:
    """
    Parametrisable decorator which checks the request method matches
    what's allowed (raising an error, if not) and responds appropriately
    to an OPTIONS request

    @param   methods  Allowed methods (strings)
    @return  Handler decorator
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
                raise error_factory(405, f"Cannot {request.method} the resource at {request.url}.", headers=allow_header)

            if request.method == "OPTIONS":
                return Response(status=200, headers=allow_header)

            return await handler(request)

        return _decorated

    return _decorator


def accept(*media_types) -> _HandlerDecoratorT:
    """
    Parametrisable decorator which checks the requested acceptable media
    types can be fulfilled (raising an error, if not)

    @param   media_types  Available media types (strings)
    @return  Handler decorator
    """
    # Available media types
    if not media_types or any(not RE_MEDIA_TYPE.match(m) for m in media_types):
        raise TypeError("You must specify fully-qualified media type(s)")

    available = tuple(set(media_types))

    def _decorator(handler:HandlerT) -> HandlerT:
        """
        Decorator that handles the accepted media types

        @param   handler  Handler function to decorate
        @return  Decorated handler
        """
        @wraps(handler)
        async def _decorated(request:Request) -> Response:
            """
            Check Accept header against acceptable media types

            @param   request  HTTP request (Request)
            @return  HTTP response (Response)
            """
            # Client accepts anything if no Accept value found
            acceptable = AcceptParser(request.headers.get("Accept", "*/*"))

            if not acceptable.can_accept(*available):
                _pretty = " or".join(", ".join(available).rsplit(",", 1))
                raise error_factory(406, f"Can only respond with {_pretty} media types")

            # Thread the parsed Accept header into the request for the
            # handler to deal with
            request["irobot_request_accept"] = acceptable
            return await handler(request)

        return _decorated

    return _decorator
