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

from typing import Awaitable, Callable, List

from aiohttp import web

from irobot.authentication import BaseAuthHandler
from irobot.httpd._common import HandlerT
from irobot.httpd._error import error_factory


def authentication_middleware(auth_handlers:List[BaseAuthHandler]) -> Callable[[web.Application, HandlerT], Awaitable[HandlerT]]:
    """
    Create the middleware factory that handles authentication with the
    given authentication handlers

    @param   auth_handlers  List of authentication handlers
    @return  Authentication middleware factory
    """

    async def _factory(app:web.Application, handler:HandlerT) -> HandlerT:
        """
        Authentication middleware factory

        @param   app      Application
        @param   handler  Route handler
        @return  Authentication middleware handler
        """

        async def _middleware(request:web.Request) -> web.Response:
            """
            Authentication middleware

            @param   request  HTTP request
            @return  HTTP response
            """

        return _middleware

    return _factory
