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
import shutil
import unittest
from uuid import uuid4

import irobot.common.canon as canon
from irobot.precache.precache import _new_precache_dir, _create_precache_dir, _delete_precache_dir


class TestPrecacheDir(unittest.TestCase):
    def setUp(self):
        while True:
            self.base = os.path.join(canon.path(os.curdir), f"test_precache_{uuid4().hex}")
            if not os.path.exists(self.base):
                break

        os.makedirs(self.base, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.base)

    def test_new_precache_dir(self):
        precache_dir = _new_precache_dir(self.base)
        self.assertRegex(precache_dir, rf"^{self.base}(/[a-f0-9]{{2}}){{16}}$")

    def test_create_precache_dir(self):
        precache_dir = _new_precache_dir(self.base)

        self.assertFalse(os.path.exists(precache_dir))
        _create_precache_dir(precache_dir)
        self.assertTrue(os.path.exists(precache_dir))
        self.assertEqual(os.stat(precache_dir).st_mode & 0o777, 0o750)

    def test_delete_precache_dir(self):
        precache_dir = _new_precache_dir(self.base)
        _create_precache_dir(precache_dir)
        self.assertTrue(os.path.exists(precache_dir))

        _delete_precache_dir(precache_dir)
        self.assertFalse(os.path.exists(precache_dir))

        parent, _top = os.path.split(precache_dir)
        self.assertTrue(os.path.exists(parent))


if __name__ == "__main__":
    unittest.main()
