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
from math import sqrt
from random import sample
from statistics import stdev

import irobot.precache.db._udf as _udf


class TestUDFs(unittest.TestCase):
    def test_stderr(self):
        stderr = _udf.StandardError()

        self.assertEqual(stderr.name, "stderr")

        # Pass over non-numeric input
        stderr.step("foo")
        self.assertIsNone(stderr.finalise())

        data = []
        for i, x in enumerate(sample(range(100), 20)):
            stderr.step(x)
            data.append(x)

            if i == 0:
                # Need at least two numeric data points
                self.assertIsNone(stderr.finalise())

            if i > 0:
                calculated = stdev(data) / sqrt(i + 1)
                self.assertAlmostEqual(stderr.finalise(), calculated)


if __name__ == "__main__":
    unittest.main()
