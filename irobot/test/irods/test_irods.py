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

import os
import unittest
import filecmp
from tempfile import gettempdir, NamedTemporaryFile

from irobot.config.irods import iRODSConfig
from irobot.irods import iRODS


# Temporary data object for testing
TEMP_DATAOBJECT_SIZE = 1024
TEMP_DATAOBJECT_DATA = os.urandom(TEMP_DATAOBJECT_SIZE)
TEMP_DATAOBJECT_METADATA = {"foo": "bar"}


# TODO Mock low-level calls to get data and metadata so they always
# return the above


class TestiRODS(unittest.TestCase):
    def setUp(self):
        config = iRODSConfig(max_connections="2")
        self.irods = iRODS(config)

        self.do_source = NamedTemporaryFile(delete=False)
        self.do_source.write(TEMP_DATAOBJECT_DATA)
        self.do_source.close()

        # We only create the target for the sake of the filename
        self.do_target = NamedTemporaryFile(delete=True)
        self.do_target.close()

    def tearDown(self):
        os.unlink(self.do_source.name)

        if os.path.exists(self.do_target.name):
            os.unlink(self.do_target.name)

    def test_get_dataobject(self):
        self.irods.get_dataobject("/foo/bar", self.do_target.name)
        self.assertTrue(filecmp.cmp(self.do_source.name, self.do_target.name))

    def test_get_metadata(self):
        avu_metadata, fs_metadata = self.irods.get_metadata("/foo/bar")
        self.assertEqual(avu_metadata, TEMP_DATAOBJECT_METADATA)
        self.assertEqual(fs_metadata, {"size": TEMP_DATAOBJECT_SIZE})

    def test_max_connections(self):
        pass


if __name__ == "__main__":
    unittest.main()
