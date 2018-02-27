import logging
import unittest

from irobot.tests.system.common import TestWithIrobot

EXAMPLE_DATA = "example-data"


class TestDataObjectEndpoint(TestWithIrobot):
    """
    Tests for iRobot's data object endpoints.
    """
    def setUp(self):
        super().setUp()
        logging.root.setLevel(logging.DEBUG)

    def test_get_when_not_in_irods(self):
        self.assertIsNone(self.request_data("/not/real"))

    def test_get_when_in_irods(self):
        data_object_location = self.upload_to_irods(EXAMPLE_DATA)
        self.assertEqual(EXAMPLE_DATA, self.request_data(data_object_location))

if __name__ == "__main__":
    unittest.main()
