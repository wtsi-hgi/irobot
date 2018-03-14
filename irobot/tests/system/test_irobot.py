import logging
import unittest
from subprocess import CalledProcessError

from irobot.tests.system._common import TestWithIrobot, BASIC_AUTHENTICATION_FAILED_STATUS_CODE

EXAMPLE_DATA = "example-data"


class TestDataObjectEndpoint(TestWithIrobot):
    """
    Tests for iRobot's data object endpoints.
    """
    def setUp(self):
        super().setUp()
        logging.root.setLevel(logging.DEBUG)

    def test_get_when_unauthorised(self):
        basic_authentication_url = f"{self.authentication_server.service.name}:" \
                                   f"{list(self.authentication_server.service.ports.keys())[0]}/" \
                                   f"{BASIC_AUTHENTICATION_FAILED_STATUS_CODE}"
        configuration_location = self.irobot.create_configuration(basic_authentication_url)
        extra_links = {self.authentication_server.service.name: self.authentication_server.service.container_id}

        with self.irobot.start_server(configuration_location, extra_links) as irobot_service:
            irobot_url = f"http://{irobot_service.host}:{irobot_service.port}"
            try:
                self.irobot.request_data("/some/data", irobot_url=irobot_url)
            except CalledProcessError as e:
                # XXX: This madness is exploiting https://github.com/wtsi-hgi/irobot-client/issues/9
                self.assertEqual(401 % 256, e.returncode)

    def test_get_when_not_in_irods(self):
        self.assertIsNone(self.irobot.request_data("/not/real"))

    def test_get_when_in_irods(self):
        data_object_location = self.irods.upload_file(EXAMPLE_DATA)
        self.assertEqual(EXAMPLE_DATA, self.irobot.request_data(data_object_location))


if __name__ == "__main__":
    unittest.main()
