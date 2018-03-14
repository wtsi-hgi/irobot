import unittest
from time import sleep
from subprocess import CalledProcessError

from irobot.tests.system.common import TestWithIrobot, BASIC_AUTHENTICATION_FAILED_STATUS_CODE

EXAMPLE_DATA = "example-data"


class TestDataObjectEndpoint(TestWithIrobot):
    """
    Tests for iRobot's data object endpoints.
    """
   
    def test_get_when_not_in_irods(self):
        print(self.irobot_url)
        sleep(1000000)

    
if __name__ == "__main__":
    unittest.main()
