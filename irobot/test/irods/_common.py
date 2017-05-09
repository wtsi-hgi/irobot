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

TEST_BATON_DICT = {
    "collection": "/foo",
    "data_object": "bar",
    "checksum": "abcdef1234567890",
    "size": 1234,
    "avus": [
        {"attribute": "foo", "value": "bar"},
        {"attribute": "quux", "value": "xyzzy", "units": "baz"}
    ],
    "access": [
        {"owner": "someone", "level": "own", "zone": "myZone"}
    ],
    "timestamps": [
        {"created": "1970-01-01T00:00:00", "replicates": 0},
        {"modified": "1970-01-02T03:04:05", "replicates": 0}
    ]
}

TEST_BATON_JSON = json.dumps(TEST_BATON_DICT)
