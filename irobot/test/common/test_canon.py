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
from datetime import timedelta

import irobot.common.canon as canon


class TestCanonicalPath(unittest.TestCase):
    """
    This is just the composition of standard library functions, so we
    presume it not to require exhaustive testing. As such, we just test
    the functional components individually to show that the composition
    has no effect on the outcome.
    """
    def test_user_expansion(self):
        self.assertEqual(canon.path("~"), os.path.expanduser("~"))

    def test_path_normalisation(self):
        for case in ["/A//B", "/A/B/", "/A/./B", "/A/foo/../B"]:
            self.assertEqual(canon.path(case), os.path.normpath(case))

    def test_abs_path(self):
        self.assertEqual(canon.path("/foo"), "/foo")
        self.assertEqual(canon.path("foo"), os.path.normpath(os.path.join(os.getcwd(), "foo")))


class TestCanonicalDuration(unittest.TestCase):
    def test(self):
        self.assertRaises(ValueError, canon.duration, "foo")
        
        self.assertIsNone(canon.duration("never"))
        self.assertIsNone(canon.duration("0s"))

        self.assertEqual(canon.duration("1s"),        timedelta(seconds=1))
        self.assertEqual(canon.duration("1.2 s"),     timedelta(seconds=1.2))
        self.assertEqual(canon.duration("1 sec"),     timedelta(seconds=1.0))
        self.assertEqual(canon.duration("2 secs"),    timedelta(seconds=2.0))
        self.assertEqual(canon.duration("3 second"),  timedelta(seconds=3.0))
        self.assertEqual(canon.duration("4 seconds"), timedelta(seconds=4.0))
        self.assertEqual(canon.duration("5 SeCoNdS"), timedelta(seconds=5.0))

        self.assertEqual(canon.duration("1m"),        timedelta(minutes=1))
        self.assertEqual(canon.duration("1.2 m"),     timedelta(minutes=1.2))
        self.assertEqual(canon.duration("1 min"),     timedelta(minutes=1.0))
        self.assertEqual(canon.duration("2 mins"),    timedelta(minutes=2.0))
        self.assertEqual(canon.duration("3 minute"),  timedelta(minutes=3.0))
        self.assertEqual(canon.duration("4 minutes"), timedelta(minutes=4.0))
        self.assertEqual(canon.duration("5 MiNuTeS"), timedelta(minutes=5.0))


class TestCanonicaliseHumanSize(unittest.TestCase):
    def test_bytes(self):
        self.assertRaises(ValueError, canon.human_size, "foo")
        self.assertRaises(ValueError, canon.human_size, "1.2B")
        self.assertRaises(ValueError, canon.human_size, "1.2 B")

        self.assertEqual(canon.human_size("1"),         1)
        self.assertEqual(canon.human_size("12"),        12)
        self.assertEqual(canon.human_size("123"),       123)
        self.assertEqual(canon.human_size("1234B"),     1234)
        self.assertEqual(canon.human_size("12345 B"),   12345)

    def test_decimal_multiplier(self):
        self.assertRaises(ValueError, canon.human_size, "1 KB")
        self.assertRaises(ValueError, canon.human_size, "1 XB")

        self.assertEqual(canon.human_size("1kB"),       1000)
        self.assertEqual(canon.human_size("1.2kB"),     1.2 * 1000)
        self.assertEqual(canon.human_size("1.23 kB"),   1.23 * 1000)
        self.assertEqual(canon.human_size("1MB"),       1000**2)
        self.assertEqual(canon.human_size("1.2MB"),     1.2 * (1000**2))
        self.assertEqual(canon.human_size("1.23 MB"),   1.23 * (1000**2))
        self.assertEqual(canon.human_size("1GB"),       1000**3)
        self.assertEqual(canon.human_size("1.2GB"),     1.2 * (1000**3))
        self.assertEqual(canon.human_size("1.23 GB"),   1.23 * (1000**3))
        self.assertEqual(canon.human_size("1TB"),       1000**4)
        self.assertEqual(canon.human_size("1.2TB"),     1.2 * (1000**4))
        self.assertEqual(canon.human_size("1.23 TB"),   1.23 * (1000**4))

    def test_binary_multiplier(self):
        self.assertRaises(ValueError, canon.human_size, "1 KiB")
        self.assertRaises(ValueError, canon.human_size, "1 kIB")
        self.assertRaises(ValueError, canon.human_size, "1 XiB")

        self.assertEqual(canon.human_size("1kiB"),      1024)
        self.assertEqual(canon.human_size("1.2kiB"),    int(1.2 * 1024))
        self.assertEqual(canon.human_size("1.23 kiB"),  int(1.23 * 1024))
        self.assertEqual(canon.human_size("1MiB"),      1024**2)
        self.assertEqual(canon.human_size("1.2MiB"),    int(1.2 * (1024**2)))
        self.assertEqual(canon.human_size("1.23 MiB"),  int(1.23 * (1024**2)))
        self.assertEqual(canon.human_size("1GiB"),      1024**3)
        self.assertEqual(canon.human_size("1.2GiB"),    int(1.2 * (1024**3)))
        self.assertEqual(canon.human_size("1.23 GiB"),  int(1.23 * (1024**3)))
        self.assertEqual(canon.human_size("1TiB"),      1024**4)
        self.assertEqual(canon.human_size("1.2TiB"),    int(1.2 * (1024**4)))
        self.assertEqual(canon.human_size("1.23 TiB"),  int(1.23 * (1024**4)))


class TestCanonicaliseIPv4(unittest.TestCase):
    def test(self):
        self.assertRaises(ValueError, canon.ipv4, "foo")
        self.assertRaises(ValueError, canon.ipv4, "999.999.999.999")
        self.assertRaises(ValueError, canon.ipv4, "0777.0777.0777.0777")
        self.assertRaises(ValueError, canon.ipv4, str(2**32))
        self.assertEqual(canon.ipv4("222.173.190.239"), "222.173.190.239")
        self.assertEqual(canon.ipv4("3735928559"), "222.173.190.239")
        self.assertEqual(canon.ipv4("0xdeadbeef"), "222.173.190.239")
        self.assertEqual(canon.ipv4("0xDE.0xAD.0xBE.0xEF"), "222.173.190.239")
        self.assertEqual(canon.ipv4("0336.0255.0276.0357"), "222.173.190.239")


class TestCanonicalDomainName(unittest.TestCase):
    def test(self):
        self.assertRaises(ValueError, canon.domain_name, "-foo")
        self.assertRaises(ValueError, canon.domain_name, "foo-")
        self.assertRaises(ValueError, canon.domain_name, "foo..bar")
        self.assertRaises(ValueError, canon.domain_name, "1234567890123456789012345678901234567890123456789012345678901234")
        self.assertEqual(canon.domain_name("foo"), "foo")
        self.assertEqual(canon.domain_name("foo."), "foo")
        self.assertEqual(canon.domain_name("foo-bar"), "foo-bar")
        self.assertEqual(canon.domain_name("foo.bar"), "foo.bar")
        self.assertEqual(canon.domain_name("foo.bar.quux"), "foo.bar.quux")
        self.assertEqual(canon.domain_name("SaNgEr.Ac.Uk"), "sanger.ac.uk")


if __name__ == "__main__":
    unittest.main()
