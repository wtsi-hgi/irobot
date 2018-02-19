import logging
import os
import tempfile
import unittest
from abc import ABCMeta
from threading import Lock

import docker
from temphelpers import TempManager

from useintest.modules.irods import IrodsDockerisedService
from useintest.modules.irods.services import IrodsServiceController
from useintest.services.builders import DockerisedServiceControllerTypeBuilder

_ROOT_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../")
_IROBOT_DOCKER_BUILD_CONTEXT = _ROOT_DIRECTORY
_IROBOT_DOCKER_BUILD_FILE = os.path.join(_ROOT_DIRECTORY, "Dockerfile")
_IROBOT_IMAGE_NAME = "mercury/irobot"
_IROBOT_BASIC_CONFIG_LOCATION = os.path.join(os.path.dirname(os.path.realpath(__file__)), "irobot.conf")

_docker_client = docker.from_env()

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


IrobotServiceController = DockerisedServiceControllerTypeBuilder(
    repository=_IROBOT_IMAGE_NAME,
    tag="latest",
    start_log_detector=lambda line: "Starting API server" in line,
    start_http_detector=lambda response: response.status_code == 401,
    ports=[5000],
    name="IrobotDockerServiceController",
    pull=False,
    start_tries=1).build()


class TestWithIrobot(unittest.TestCase, metaclass=ABCMeta):
    """
    Test that uses iRobot.
    """
    _docker_client = docker.from_env()
    _irobot_built = False

    @staticmethod
    def _build_irobot() -> str:
        if not TestWithIrobot._irobot_built:
            log_generator =_docker_client.api.build(
                path=_IROBOT_DOCKER_BUILD_CONTEXT, dockerfile=_IROBOT_DOCKER_BUILD_FILE,
                tag=_IROBOT_IMAGE_NAME, decode=True)
            for log in log_generator:
                details = log.get("stream", "").strip()
                if len(details) > 0:
                    logger.debug(details)

            TestWithIrobot._irobot_built = True

        return _IROBOT_IMAGE_NAME

    @classmethod
    def setUpClass(cls):
        temp_directory = tempfile.gettempdir()
        if temp_directory.startswith("/var/folders/"):
            # By default, Docker-for-Mac cannot mount /var, therefore ensure temps are created in /tmp
            temp_directory = "/tmp"
        cls._temp_manager = TempManager(
            default_mkdtemp_kwargs=dict(dir=temp_directory), default_mkstemp_kwargs=dict(dir=temp_directory))

        cls._irods_lock = Lock()
        cls._irods_controller = None
        cls._irods_service = None
        cls._irods_environment_location = None

    @classmethod
    def tearDownClass(cls):
        with cls._irods_lock:
            if cls._irods_service is not None:
                cls._irods_controller.stop_service(cls._irods_service)

    @classmethod
    def get_irods(cls) -> IrodsDockerisedService:
        if cls._irods_service is None:
            with cls._irods_lock:
                if cls._irods_service is None:
                    cls._irods_controller = IrodsServiceController()
                    cls._irods_service = cls._irods_controller.start_service()
        return cls._irods_service

    @property
    def irods_environment_location(self):
        if self._irods_environment_location is None:
            _, self._irods_environment_location = self._temp_manager.create_temp_file()
            os.remove(self._irods_environment_location)
            IrodsServiceController.write_connection_settings(self._irods_environment_location, self.get_irods())
        return self._irods_environment_location

    @property
    def irobot(self):
        if self._irobot_service is None:
            self._build_irobot()
            self._irobot_controller = IrobotServiceController()
            self._irobot_service = self._irobot_controller.start_service(dict(
                volumes={self.irods_environment_location: dict(bind="/root/.irods/irods_environment.json", mode="ro"),
                         _IROBOT_BASIC_CONFIG_LOCATION: dict(bind="/root/irobot.conf", mode="ro")},
                environment={"IRODS_PASSWORD": self.get_irods().root_user.password},
                links={self.get_irods().container_id: self.get_irods().container_id}))
        return self._irobot_service

    def setUp(self):
        self._irobot_controller = None
        self._irobot_service = None

    def tearDown(self):
        self._temp_manager.tear_down()
        if self._irobot_service is not None:
            self._irobot_controller.stop_service(self._irobot_service)
