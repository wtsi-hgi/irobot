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

from aiohttp import web

from irobot.authentication import BaseAuthHandler
from irobot.httpd._common import HandlerT
from irobot.httpd._error import error_factory


_HTTPAuthenticationFailure = error_factory(401, "Could not authenticate credentials")


async def authentication_middleware(app:web.Application, handler:HandlerT) -> HandlerT:
    """
    Authentication middleware factory

    @param   app      Application
    @param   handler  Route handler
    @return  Authentication middleware handler
    """

    # Get authentication handlers
    auth_handlers = app.get("irobot_auth_handlers", [])

    async def _middleware(request:web.Request) -> web.Response:
        """
        Authentication middleware

        @param   request  HTTP request
        @return  HTTP response
        """
        try:
            auth_header = request.headers["Authorization"]
        except KeyError:
            # Fail on missing Authorization header
            raise _HTTPAuthenticationFailure

        user = None
        for auth_handler in auth_handlers:
            # TODO The authentication handler should probably also
            # be asynchronous. This is planned with the deprecation
            # of the requests library (all our authentication
            # handlers are currently HTTP-based)
            user = auth_handler.authenticate(auth_header)
            if user:
                # Short-circuit if authentication succeeded
                break

        if not user:
            # Fail on inability to authenticate
            raise _HTTPAuthenticationFailure

        # Success: Thread the authenticated user into the request
        request["auth_user"] = user
        return await handler(request)

    return _middleware
