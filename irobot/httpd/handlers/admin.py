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

from irobot.config import ConfigJSONEncoder
from irobot.httpd._common import ENCODING
from irobot.httpd.handlers import _decorators as request
from irobot.precache.precache import Datatype


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

    precache = req.app["irobot_precache"]

    production_rates = {
        process: {
            "average": rate.mean if rate else None,
            "stderr":  rate.stderr if rate else None
        }
        for process, rate in precache.production_rates.items()
    }

    irobot_status:Dict = {
        "connections": {
            "active": req.app["irobot_connections_active"],
            "total":  req.app["irobot_connections_total"],
            "since":  req.app["irobot_start_time"]
        },
        "precache": {
            "commitment": precache.commitment,
            "checksum_rate": production_rates[Datatype.checksums]
        },
        "irods": {
            "active": precache.current_downloads,
            "download_rate": production_rates[Datatype.data]
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

    body = json.dumps(req.app["irobot_config"], cls=ConfigJSONEncoder).encode(ENCODING)
    content_length = len(body)

    if req.method == "GET":
        resp.body = body

    if req.method == "HEAD":
        resp.headers["Content-Length"] = f"{content_length}"

    return resp


@request.allow("GET", "HEAD")
@request.accept(_json)
async def manifest(req:Request) -> Response:
    """
    Precache manifest handler

    @param   request  HTTP request (Request)
    @return  HTTP response (Response)
    """
    assert req["irobot_preferred"] == _json

    resp = Response(status=200, content_type=_json, charset=ENCODING)

    precache_manifest:List[Dict] = [
        {
            "path": data_object.irods_path,
            "availability": {
                "data":      data_object.status[Datatype.data],
                "metadata":  data_object.status[Datatype.metadata],
                "checksums": data_object.status[Datatype.checksums]
            }
        }
        for data_object in req.app["irobot_precache"]
    ]

    body = json.dumps(precache_manifest).encode(ENCODING)
    content_length = len(body)

    if req.method == "GET":
        resp.body = body

    if req.method == "HEAD":
        resp.headers["Content-Length"] = f"{content_length}"

    return resp
