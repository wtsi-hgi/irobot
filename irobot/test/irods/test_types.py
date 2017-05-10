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

from irobot.irods._types import AVU, Metadata, MetadataJSONDecoder, MetadataJSONEncoder
from irobot.test.irods._common import TEST_BATON_DICT, TEST_BATON_JSON


class TestMetadata(unittest.TestCase):
    def test_types(self):
        created = datetime(1981, 9, 25)
        modified = datetime.utcnow()
        avus = [AVU("foo", "bar")]

        m = Metadata("abc", 123, created, modified, avus)
        self.assertEqual(m.checksum, "abc")
        self.assertEqual(m.size, 123)
        self.assertEqual(m.created, created)
        self.assertEqual(m.modified, modified)
        self.assertEqual(m.avus, avus)

        m2 = Metadata("abc", 123, created, modified, avus)
        self.assertEqual(m, m2)

    def test_decoding(self):
        m = json.loads(TEST_BATON_JSON, cls=MetadataJSONDecoder)
        self.assertEqual(m.checksum, TEST_BATON_DICT["checksum"])
        self.assertEqual(m.size, TEST_BATON_DICT["size"])
        self.assertEqual(m.created, datetime(1970, 1, 1))  # FIXME Hardcoded
        self.assertEqual(m.modified, datetime(1970, 1, 2, 3, 4, 5))  # FIXME Hardcoded
        self.assertEqual(m.avus, [AVU(**avu) for avu in TEST_BATON_DICT["avus"]])

    def test_encoding(self):
        m = json.loads(TEST_BATON_JSON, cls=MetadataJSONDecoder)
        j = json.dumps(m, cls=MetadataJSONEncoder)

        raw = json.loads(j)
        self.assertEqual(raw, {
            "timestamps": [
                {k:v}
                for ts in TEST_BATON_DICT["timestamps"]
                for k, v in ts.items()
                if k in ["created", "modified"]
            ],

            **{k: TEST_BATON_DICT[k] for k in ["checksum", "size", "avus"]}
        })

        # Test pass-through encoding
        self.assertEqual(json.dumps("foo", cls=MetadataJSONEncoder), "\"foo\"")


if __name__ == "__main__":
    unittest.main()
