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
import os
import unittest
from subprocess import CalledProcessError
from tempfile import TemporaryFile
from unittest.mock import patch

from irobot.irods._api import iRODSError, _invoke, ils, iget, baton
from irobot.irods._types import MetadataJSONDecoder
from irobot.test.irods._common import TEST_BATON_JSON


class TestInvocation(unittest.TestCase):
    def test_simple(self):
        exit_code, stdout, stderr = _invoke("whoami")
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout, "{USER}\n".format(**os.environ))
        self.assertEqual(stderr, "")

    def test_tuple(self):
        exit_code, stdout, stderr = _invoke(("id", "-un"))
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout, "{USER}\n".format(**os.environ))
        self.assertEqual(stderr, "")

    def test_shell(self):
        exit_code, stdout, stderr = _invoke("echo 'foo' && echo 'bar' >&2 && exit 123", shell=True)
        self.assertEqual(exit_code, 123)
        self.assertEqual(stdout, "foo\n")
        self.assertEqual(stderr, "bar\n")

    def test_stdin_string(self):
        exit_code, stdout, stderr = _invoke("cat", "mouse")
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout, "mouse")
        self.assertEqual(stderr, "")

    def test_stdin_fd(self):
        with TemporaryFile(mode="w+t") as stdin:
            stdin.write("mouse")
            stdin.flush()
            stdin.seek(0)

            exit_code, stdout, stderr = _invoke("cat", stdin.fileno())
            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout, "mouse")
            self.assertEqual(stderr, "")

    def test_stdin_file(self):
        with TemporaryFile(mode="w+t") as stdin:
            stdin.write("mouse")
            stdin.flush()
            stdin.seek(0)

            exit_code, stdout, stderr = _invoke("cat", stdin)
            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout, "mouse")
            self.assertEqual(stderr, "")


@patch("irobot.irods._api._invoke")
class TestiRODSAPI(unittest.TestCase):
    def setUp(self):
        self.mock_invoke_pass = (0, "{\"foo\":\"bar\"}", "")
        self.mock_invoke_fail = (1, "", "")

    def test_ils_pass(self, mock_invoke):
        mock_invoke.return_value = self.mock_invoke_pass
        ils("/foo/bar")
        mock_invoke.assert_called_once_with(["ils", "/foo/bar"])

    def test_ils_fail(self, mock_invoke):
        mock_invoke.return_value = self.mock_invoke_fail
        self.assertRaises(iRODSError, ils, "/foo/bar")

    def test_iget_pass(self, mock_invoke):
        mock_invoke.return_value = self.mock_invoke_pass
        iget("/foo/bar", "/quux/xyzzy")
        mock_invoke.assert_called_once_with(["iget", "-f", "/foo/bar", "/quux/xyzzy"])

    def test_iget_fail(self, mock_invoke):
        mock_invoke.return_value = self.mock_invoke_fail
        self.assertRaises(iRODSError, iget, "/foo/bar", "/quux/xyzzy")

    def test_baton_pass(self, mock_invoke):
        mock_invoke.return_value = (0, TEST_BATON_JSON, "")
        self.assertEqual(baton("/foo/bar"), json.loads(TEST_BATON_JSON, cls=MetadataJSONDecoder))
        mock_invoke.assert_called_once_with(["baton-list", "--avu", "--size", "--checksum", "--acl", "--timestamp"],
                                            "{\"collection\":\"/foo\",\"data_object\":\"bar\"}")

    def test_baton_fail(self, mock_invoke):
        mock_invoke.return_value = self.mock_invoke_fail
        self.assertRaises(CalledProcessError, baton, "/foo/bar")


if __name__ == "__main__":
    unittest.main()
