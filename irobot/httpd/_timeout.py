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

import asyncio

from aiohttp import web
from async_timeout import timeout

from irobot.httpd._common import HandlerT
from irobot.httpd._error import error_factory


_HTTPResponseTimeout = error_factory(504, "Response timed out")


async def timeout_middleware(app:web.Application, handler:HandlerT) -> HandlerT:
    """
    Timeout middleware factory

    @param   app      Application
    @param   handler  Route handler
    @return  Timeout middleware handler
    """

    # Get response timeout, in seconds (None for unlimited)
    response_timeout = app.get("timeout", None)
    if response_timeout:
        response_timeout /= 1000

    async def _middleware(request:web.Request) -> web.Response:
        """
        Timeout middleware

        @note    The response timeout value is threaded through the
                 application under the "timeout" key

        @param   request  HTTP request
        @return  HTTP response
        """
        try:
            with timeout(response_timeout, loop=app.loop):
                return await handler(request)

        except asyncio.TimeoutError:
            raise _HTTPResponseTimeout

    return _middleware
