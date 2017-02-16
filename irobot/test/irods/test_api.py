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
from subprocess import CalledProcessError
from tempfile import TemporaryFile
from unittest.mock import MagicMock

import irobot.irods._api as api


_original_invoke = api._invoke
_mock_invoke = MagicMock()
_mock_invoke_pass = (0, "{\"foo\":\"bar\"}", "")
_mock_invoke_fail = (1, "", "")


class TestInvocation(unittest.TestCase):
    def setUp(self):
        api._invoke = _original_invoke

    def test_simple(self):
        exit_code, stdout, stderr = api._invoke("whoami")
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout, "{USER}\n".format(**os.environ))
        self.assertEqual(stderr, "")

    def test_tuple(self):
        exit_code, stdout, stderr = api._invoke(("id", "-un"))
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout, "{USER}\n".format(**os.environ))
        self.assertEqual(stderr, "")

    def test_shell(self):
        exit_code, stdout, stderr = api._invoke("echo 'foo' && echo 'bar' >&2 && exit 123", shell=True)
        self.assertEqual(exit_code, 123)
        self.assertEqual(stdout, "foo\n")
        self.assertEqual(stderr, "bar\n")

    def test_stdin_string(self):
        exit_code, stdout, stderr = api._invoke("cat", "mouse")
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout, "mouse")
        self.assertEqual(stderr, "")

    def test_stdin_fd(self):
        with TemporaryFile(mode="w+t") as stdin:
            stdin.write("mouse")
            stdin.flush()
            stdin.seek(0)

            exit_code, stdout, stderr = api._invoke("cat", stdin.fileno())
            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout, "mouse")
            self.assertEqual(stderr, "")

    def test_stdin_file(self):
        with TemporaryFile(mode="w+t") as stdin:
            stdin.write("mouse")
            stdin.flush()
            stdin.seek(0)

            exit_code, stdout, stderr = api._invoke("cat", stdin)
            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout, "mouse")
            self.assertEqual(stderr, "")


class TestiRODSAPI(unittest.TestCase):
    def setUp(self):
        api._invoke = _mock_invoke

    def tearDown(self):
        api._invoke.reset_mock()

    def test_ils_pass(self):
        api._invoke.return_value = _mock_invoke_pass
        api.ils("/foo/bar")
        api._invoke.assert_called_once_with(["ils", "/foo/bar"])

    def test_ils_fail(self):
        api._invoke.return_value = _mock_invoke_fail
        self.assertRaises(CalledProcessError, api.ils, "/foo/bar")

    def test_iget_pass(self):
        api._invoke.return_value = _mock_invoke_pass
        api.iget("/foo/bar", "/quux/xyzzy")
        api._invoke.assert_called_once_with(["iget", "-f", "/foo/bar", "/quux/xyzzy"])

    def test_iget_fail(self):
        api._invoke.return_value = _mock_invoke_fail
        self.assertRaises(CalledProcessError, api.iget, "/foo/bar", "/quux/xyzzy")

    def test_baton_pass(self):
        api._invoke.return_value = _mock_invoke_pass
        self.assertEqual(api.baton("/foo/bar"), {"foo": "bar"})
        api._invoke.assert_called_once_with(["baton-list", "--avu", "--size", "--checksum", "--acl", "--timestamp"],
                                            "{\"collection\":\"/foo\",\"data_object\":\"bar\"}")

    def test_baton_fail(self):
        api._invoke.return_value = _mock_invoke_fail
        self.assertRaises(CalledProcessError, api.baton, "/foo/bar")


if __name__ == "__main__":
    unittest.main()
