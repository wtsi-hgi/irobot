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
import json
import logging

import async_timeout
from aiohttp import web

from irobot.httpd._common import ENCODING, HandlerT
from irobot.httpd._error import error_factory


_HTTPResponseTimeout = error_factory(504, "Response timed out")


async def log_connections(app:web.Application, handler:HandlerT) -> HandlerT:
    """
    Keep a log of all active and current connections, seeing as we don't
    appear to be able to access this information from elsewhere

    @param   app      Application
    @param   handler  Route handler
    @return  Connection counting middleware handler
    """
    async def _middleware(request:web.Request) -> web.Response:
        """
        Connection counting middleware

        @param   request  HTTP request
        @return  HTTP response
        """
        app["irobot_connections_total"] += 1
        app["irobot_connections_active"] += 1

        try:
            return await handler(request)
        finally:
            app["irobot_connections_active"] -= 1

    return _middleware


async def catch500(app:web.Application, handler:HandlerT) -> HandlerT:
    """
    Internal server error catch-all factory

    @param   app      Application
    @param   handler  Route handler
    @return  HTTP 500 response middleware handler
    """
    def _log(message:str) -> None:
        """ Convenience wrapper to do logging """
        if app.logger:
            app.logger.log(logging.ERROR, message)

    async def _middleware(request:web.Request) -> web.Response:
        """
        HTTP 500 response middleware

        @param   request  HTTP request
        @return  HTTP response
        """
        try:
            return await handler(request)

        except web.HTTPError as e:
            message = json.loads(e.body, encoding=ENCODING)["description"]
            _log(message)
            raise

        except Exception as e:
            message = str(e)
            _log(message)
            raise error_factory(500, message)

    return _middleware


async def timeout(app:web.Application, handler:HandlerT) -> HandlerT:
    """
    Timeout middleware factory

    @note    The response timeout value is threaded through the
             application under the "irobot_timeout" key

    @param   app      Application
    @param   handler  Route handler
    @return  Timeout middleware handler
    """

    # Get response timeout, in seconds (None for unlimited)
    response_timeout = app.get("irobot_timeout", None)
    if response_timeout is not None:
        response_timeout = response_timeout.total_seconds()

    async def _middleware(request:web.Request) -> web.Response:
        """
        Timeout middleware

        @param   request  HTTP request
        @return  HTTP response
        """
        try:
            with async_timeout.timeout(response_timeout, loop=app.loop):
                return await handler(request)

        except asyncio.TimeoutError:
            raise _HTTPResponseTimeout

    return _middleware


async def authentication(app:web.Application, handler:HandlerT) -> HandlerT:
    """
    Authentication middleware factory

    @note    The authentication handlers are threaded through the
             application under the "irobot_auth_handlers" key

    @param   app      Application
    @param   handler  Route handler
    @return  Authentication middleware handler
    """

    # Get authentication handlers and set WWW-Authenticate value
    auth_handlers = app.get("irobot_auth_handlers", [])
    www_authenticate = ", ".join(auth_method.www_authenticate for auth_method in auth_handlers)

    # Set up HTTP 401 response/exception
    HTTPAuthenticationFailure = error_factory(401, "Could not authenticate credentials",
                                              headers={"WWW-Authenticate": www_authenticate})

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
            raise HTTPAuthenticationFailure

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
            raise HTTPAuthenticationFailure

        # Success: Thread the authenticated user into the request
        request["irobot_auth_user"] = user
        return await handler(request)

    return _middleware
