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
from tempfile import TemporaryDirectory

from irobot.precache._dir_utils import new_name, create, delete


class TestDirUtils(unittest.TestCase):
    def setUp(self):
        self.base = TemporaryDirectory()

    def tearDown(self):
        self.base.cleanup()

    def test_new_name(self):
        precache_dir = new_name(self.base.name)
        self.assertRegex(precache_dir, rf"^{self.base.name}(/[a-f0-9]{{2}}){{16}}$")

    def test_create(self):
        precache_dir = new_name(self.base.name)

        self.assertFalse(os.path.exists(precache_dir))
        create(precache_dir)
        self.assertTrue(os.path.exists(precache_dir))
        self.assertEqual(os.stat(precache_dir).st_mode & 0o777, 0o750)

    def test_delete(self):
        precache_dir = new_name(self.base.name)
        create(precache_dir)
        self.assertTrue(os.path.exists(precache_dir))

        delete(precache_dir)
        self.assertFalse(os.path.exists(precache_dir))

        parent, _top = os.path.split(precache_dir)
        self.assertTrue(os.path.exists(parent))


if __name__ == "__main__":
    unittest.main()
