import logging
import unittest

from irobot.tests.system.common import TestWithIrobot


class TestExample(TestWithIrobot):
    """
    TODO
    """
    def setUp(self):
        logging.root.setLevel(logging.DEBUG)

    def test_stuff(self):
        self.upload_to_irods("test")
        print(self.irobot)


if __name__ == "__main__":
    unittest.main()
