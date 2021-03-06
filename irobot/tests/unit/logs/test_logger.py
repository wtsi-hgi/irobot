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

import time
import unittest
from datetime import datetime, timezone
from logging import Logger
from tempfile import NamedTemporaryFile
from unittest.mock import MagicMock, patch

from irobot.logs import logger
from irobot.config import LoggingConfig
from irobot.config._tree_builder import ConfigValue

# Mock logger's timestamper
logger.time = MagicMock(spec=time)


def _set_log_time(t: datetime):
    logger.time.gmtime.return_value = t.replace(tzinfo=timezone.utc).timetuple()


class TestLogWriter(unittest.TestCase):
    def test_no_logger(self):
        l = logger.LogWriter()
        self.assertIsNone(l.log(123, "foo"))

    def test_logger(self):
        _logger = MagicMock(spec=Logger)
        l = logger.LogWriter(_logger)

        l.log(123, "foo", "bar", quux="xyzzy")
        _logger.log.assert_called_once_with(123, "foo", "bar", quux="xyzzy")


class TestLoggerCreation(unittest.TestCase):
    def test_create_logger(self):
        with NamedTemporaryFile(mode="w+t") as log_file:
            config = LoggingConfig()
            config.add_value("output", ConfigValue(log_file.name, str))
            config.add_value("level", ConfigValue(10, int))
            log = logger.create_logger(config)

            _set_log_time(datetime(1970, 1, 1))
            log.debug("foo")

            _set_log_time(datetime(1981, 9, 25, 5, 55))
            log.info("Hello World!")

            # Rewind and read contents of log file
            log_file.flush()
            log_file.seek(0)
            logged = log_file.readlines()

            self.assertEqual(logged[0], "1970-01-01T00:00:00Z+0000\tDEBUG\tfoo\n")
            self.assertEqual(logged[1], "1981-09-25T05:55:00Z+0000\tINFO\tHello World!\n")


@patch("irobot.logs.logger.sys.exit", spec=True)
class TestExceptionHandler(unittest.TestCase):
    def setUp(self):
        self.log = MagicMock(spec=Logger)
        self.handler = logger._exception_handler(self.log)

    def test_normal_exception(self, mock_sys_exit):
        exc = Exception("foo")
        self.handler(exc.__class__, exc, None)

        self.log.critical.assert_called_once_with(str(exc))
        mock_sys_exit.assert_called_once_with(1)

    def test_keyboard_interrupt(self, mock_sys_exit):
        exc = KeyboardInterrupt()
        self.assertIsNone(self.handler(exc.__class__, exc, None))

        self.log.critical.assert_not_called()
        mock_sys_exit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
