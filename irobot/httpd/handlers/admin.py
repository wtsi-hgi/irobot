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
from datetime import datetime
from typing import Dict, List

from aiohttp.web import Request, Response

from irobot.common import AsyncTaskStatus, DataObjectState, ISO8601_UTC
from irobot.config import ConfigJSONEncoder
from irobot.httpd._common import ENCODING
from irobot.httpd.handlers import _decorators as request
from irobot.precache import DataObject


_json = "application/json"


def _human_readable_status(data_object:DataObject, datatype:DataObjectState) -> str:
    """
    Human readable status of data object state

    @param   data_object  iRODS data object (DataObject)
    @param   datatype     Datatype (DataObjectState)
    @return  Human readable string
    """
    if data_object.status[datatype] == AsyncTaskStatus.finished:
        return "Ready"

    if datatype == DataObjectState.metadata:
        # Metadata doesn't have a production rate, so if it isn't
        # available, then it's pending
        return "Pending"

    # TODO Get ETA from InProgress exception
    return "Pending"


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
            "checksum_rate": production_rates[DataObjectState.checksums]
        },
        "irods": {
            "active": precache.current_downloads,
            "download_rate": production_rates[DataObjectState.data]
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
                datatype.name: _human_readable_status(data_object, datatype)
                for datatype in DataObjectState
            },
            "last_accessed": datetime.strftime(data_object.last_accessed, ISO8601_UTC),
            "contention": data_object.contention,
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
