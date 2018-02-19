import logging
import unittest

from irobot.tests.system.common import TestWithIrobot


class TestExample(TestWithIrobot):
    def test_stuff(self):
        logging.root.setLevel(logging.DEBUG)
        self.irobot()


if __name__ == "__main__":
    unittest.main()
