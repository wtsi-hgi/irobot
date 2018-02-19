import unittest
from abc import ABCMeta
from subprocess import check_output

import os

import sys
from useintest.modules.irods import IrodsDockerisedService
from useintest.modules.irods.services import IrodsServiceController

_IROBOT_BUILD_SCRIPT = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../build.sh")
_IROBOT_USER = "rods"
_IROBOT_IMAGE_NAME = f"hgi/irobot:{_IROBOT_USER}"


class TestWithIrobot(unittest.TestCase, metaclass=ABCMeta):
    """
    TODO
    """
    @staticmethod
    def _build_irobot() -> str:
        check_output([_IROBOT_BUILD_SCRIPT, "native", _IROBOT_USER], stderr=sys.stderr)
        return _IROBOT_IMAGE_NAME

    @property
    def irods(self) -> IrodsDockerisedService:
        if self._irods_service is None:
            self._irods_controller = IrodsServiceController()
            self._irods_service = self._irods_controller.start_service()
        return self._irods_service

    @property
    def irobot(self):
        raise NotImplementedError()

    def setUp(self):
        self._irods_controller = None
        self._irods_service = None


class TestExample(TestWithIrobot):
    def test_stuff(self):
        self._build_irobot()


# del TestWithIrobot



if __name__ == "__main__":
    unittest.main()
