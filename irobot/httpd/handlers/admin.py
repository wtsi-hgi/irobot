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

from aiohttp.web import Request, Response

from irobot.httpd.handlers import _decorators as request


@request.allow("GET", "HEAD")
@request.accept("application/json")
async def status(req:Request) -> Response:
    """
    Status handler

    @param   request  HTTP request (Request)
    @return  HTTP response (Response)
    """
    raise NotImplementedError("OMG!!")


@request.allow("GET", "HEAD")
@request.accept("application/json")
async def config(req:Request) -> Response:
    """
    Config status handler

    @note    Is this necessary?...

    @param   request  HTTP request (Request)
    @return  HTTP response (Response)
    """
    raise NotImplementedError("OMG!!")


@request.allow("GET", "HEAD")
@request.accept("application/json")
async def precache(req:Request) -> Response:
    """
    Precache status handler

    @param   request  HTTP request (Request)
    @return  HTTP response (Response)
    """
    raise NotImplementedError("OMG!!")
