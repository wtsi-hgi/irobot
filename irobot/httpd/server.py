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
import logging
from typing import List, Optional

from aiohttp import web

from irobot.authentication import BaseAuthHandler
from irobot.config.httpd import HTTPdConfig
from irobot.httpd import _middleware, handlers
from irobot.precache import Precache


_noop = lambda *_, **__: None


async def _set_server_header(_request:web.Request, response:web.Response) -> None:
    """ Set the Server response header """
    response.headers["Server"] = "iRobot"


async def _shutdown_server(app:web.Application) -> None:
    """ Gracefully shutdown the HTTPd server """
    if app.logger:
        app.logger.log(logging.INFO, "Shutting down API server")

    app.loop.call_soon_threadsafe(app.loop.stop)


def start_httpd(httpd_config:HTTPdConfig, precache:Precache, auth_handlers:List[BaseAuthHandler], logger:Optional[logging.Logger] = None) -> None:
    """
    Start the HTTPd API server on the event loop of the current context

    @param   httpd_config   HTTPd configuration (HTTPdConfig)
    @param   precache       Precache interface (Precache)
    @param   auth_handlers  Authentication handlers (list of BaseAuthHandler)
    @param   logger         Logger
    """
    app = web.Application(logger=logger, middlewares=[_middleware.log_connections,
                                                      _middleware.catch500,
                                                      _middleware.timeout,
                                                      _middleware.authentication])

    # Thread through application variables
    app["irobot_config"] = httpd_config.parent
    app["irobot_timeout"] = httpd_config.timeout
    app["irobot_precache"] = precache
    app["irobot_auth_handlers"] = auth_handlers

    # This doesn't seem like a very satisfactory solution :P
    app["irobot_connections_active"] = 0
    app["irobot_connections_total"] = 0

    # Routing
    app.router.add_route("*", "/_status", handlers.status)
    app.router.add_route("*", "/_config", handlers.config)
    app.router.add_route("*", "/_precache", handlers.precache)
    app.router.add_route("*", "/{irods_path:.*}", handlers.data_object)

    # Signal handlers
    app.on_response_prepare.append(_set_server_header)
    app.on_shutdown.append(_shutdown_server)

    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)

    if logger:
        logger.log(logging.INFO, f"Starting API server on http://{httpd_config.bind_address}:{httpd_config.listen}")

    web.run_app(app, host=httpd_config.bind_address, port=httpd_config.listen,
                     access_log=logger, access_log_format="%a %l %u \"%r\" %s %b",
                     print=_noop, loop=loop)
