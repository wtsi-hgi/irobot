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

import unittest
import os

from irobot.common import canonical_path


class TestCanonicalPath(unittest.TestCase):
    """
    This is just the composition of standard library functions, so we
    presume it not to require exhaustive testing. As such, we just test
    the functional components individually to show that the composition
    has no effect on the outcome.
    """
    def test_user_expansion(self):
        self.assertEquals(canonical_path("~"), os.path.expanduser("~"))

    def test_path_normalisation(self):
        for case in ["/A//B", "/A/B/", "/A/./B", "/A/foo/../B"]:
            self.assertEquals(canonical_path(case), os.path.normpath(case))

    def test_abs_path(self):
        self.assertEquals(canonical_path("/foo"), "/foo")
        self.assertEquals(canonical_path("foo"), os.path.normpath(os.path.join(os.getcwd(), "foo")))


if __name__ == "__main__":
    unittest.main()
