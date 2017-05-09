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
import unittest
from datetime import datetime

from irobot.irods._types import Metadata, MetadataJSONDecoder, MetadataJSONEncoder


TEST_BATON_JSON = json.dumps({
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
})


class TestMetadata(unittest.TestCase):
    def test_type(self):
        created = datetime(1981, 9, 25)
        modified = datetime.utcnow()
        avus = [{"attribute": "foo", "value": "bar"}]

        m = Metadata("abc", 123, created, modified, avus)
        self.assertEqual(m.checksum, "abc")
        self.assertEqual(m.size, 123)
        self.assertEqual(m.created, created)
        self.assertEqual(m.modified, modified)
        self.assertEqual(m.avus, avus)

    def test_decoding(self):
        m = json.loads(TEST_BATON_JSON, cls=MetadataJSONDecoder)
        self.assertEqual(m.checksum, "abcdef1234567890")
        self.assertEqual(m.size, 1234)
        self.assertEqual(m.created, datetime(1970, 1, 1))
        self.assertEqual(m.modified, datetime(1970, 1, 2, 3, 4, 5))
        self.assertEqual(m.avus, [
            {"attribute": "foo", "value": "bar"},
            {"attribute": "quux", "value": "xyzzy", "units": "baz"}
        ])

    def test_encoding(self):
        m = json.loads(TEST_BATON_JSON, cls=MetadataJSONDecoder)
        j = json.dumps(m, cls=MetadataJSONEncoder)
        raw = json.loads(j)
        self.assertEqual(raw, {
            "checksum": "abcdef1234567890",
            "size": 1234,
            "avus": [
                {"attribute": "foo", "value": "bar"},
                {"attribute": "quux", "value": "xyzzy", "units": "baz"}
            ],
            "timestamps": [
                {"created": "1970-01-01T00:00:00"},
                {"modified": "1970-01-02T03:04:05"}
            ]
        })


if __name__ == "__main__":
    unittest.main()
