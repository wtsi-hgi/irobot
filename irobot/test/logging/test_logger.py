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
import time
import unittest
from datetime import datetime
from tempfile import NamedTemporaryFile

from mock import MagicMock

import irobot.logging.logger as logger
from irobot.common import type_check_arguments, utc
from irobot.config.log import LoggingConfig


# Mock logger's timestamper
logger.time = MagicMock(spec=time)

@type_check_arguments(t=datetime)
def _set_log_time(t):
    logger.time.gmtime.return_value = t.replace(tzinfo=utc).timetuple()


class TestLoggerCreation(unittest.TestCase):
    def test_create_logger(self):
        with NamedTemporaryFile() as log_file:
            config = LoggingConfig(log_file.name, "debug")
            log = logger.create_logger(config)

            _set_log_time(datetime(1970, 1, 1))
            log.debug("foo")

            _set_log_time(datetime(1981, 9, 25, 5, 55))
            log.info("Hello World!")

            # Rewind and read contents of log file
            log_file.flush()
            log_file.seek(0)
            logged = log_file.readlines()

            self.assertEqual(logged[0], "1970-01-01T00:00:00Z+00:00\tDEBUG\tfoo\n")
            self.assertEqual(logged[1], "1981-09-25T05:55:00Z+00:00\tINFO\tHello World!\n")


if __name__ == "__main__":
    unittest.main()
