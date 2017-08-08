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
from typing import Dict, List

from aiohttp.web import Request, Response

from irobot.httpd._common import ENCODING
from irobot.httpd.handlers import _decorators as request


_json = "application/json"


@request.allow("GET", "HEAD")
@request.accept(_json)
async def status(req:Request) -> Response:
    """
    Status handler

    @param   request  HTTP request (Request)
    @return  HTTP response (Response)
    """
    assert req["irobot_preferred"] == _json

    resp = Response(status=200, content_type=_json, charset=ENCODING)

    irobot_status:Dict = {
        "connections": {
            "active": req.app["irobot_connections_active"],
            "total":  req.app["irobot_connections_total"],
            "since":  req.app["irobot_start_time"]
        },
        "precache": {
            "commitment": 123,
            "checksum_rate": {
                "average": 123,
                "stderr":  123
            }
        },
        "irods": {
            "active": 123,
            "download_rate": {
                "average": 123,
                "stderr": 123
            }
        }
    }

    body = json.dumps(irobot_status).encode(ENCODING)
    content_length = len(body)

    if req.method == "GET":
        resp.body = body

    if req.method == "HEAD":
        resp.headers["Content-Length"] = f"{content_length}"

    return resp


@request.allow("GET", "HEAD")
@request.accept(_json)
async def config(req:Request) -> Response:
    """
    Config status handler

    @param   request  HTTP request (Request)
    @return  HTTP response (Response)
    """
    assert req["irobot_preferred"] == _json

    resp = Response(status=200, content_type=_json, charset=ENCODING)

    irobot_config:Dict = {}

    body = json.dumps(irobot_config).encode(ENCODING)
    content_length = len(body)

    if req.method == "GET":
        resp.body = body

    if req.method == "HEAD":
        resp.headers["Content-Length"] = f"{content_length}"

    return resp


@request.allow("GET", "HEAD")
@request.accept(_json)
async def precache(req:Request) -> Response:
    """
    Precache status handler

    @param   request  HTTP request (Request)
    @return  HTTP response (Response)
    """
    assert req["irobot_preferred"] == _json

    resp = Response(status=200, content_type=_json, charset=ENCODING)

    irobot_precache:List[Dict] = []

    body = json.dumps(irobot_precache).encode(ENCODING)
    content_length = len(body)

    if req.method == "GET":
        resp.body = body

    if req.method == "HEAD":
        resp.headers["Content-Length"] = f"{content_length}"

    return resp
