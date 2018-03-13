import logging
import os
import subprocess
import tempfile
import unittest
from abc import ABCMeta
from configparser import ConfigParser
from tempfile import TemporaryDirectory
from threading import Lock
from typing import Dict, Optional
from uuid import uuid4

import docker
from irods.session import iRODSSession
from temphelpers import TempManager

from useintest.modules.irods import IrodsDockerisedService
from useintest.modules.irods.services import IrodsServiceController
from useintest.services.builders import DockerisedServiceControllerTypeBuilder
from useintest.services.models import DockerisedService

# By default, Docker-for-Mac cannot mount /var, therefore ensure temps are created in /tmp
MOUNTABLE_TEMP_DIRECTORY = tempfile.gettempdir() if not tempfile.gettempdir().startswith("/var/folders/") else "/tmp"

BASIC_AUTHENTICATION_SUCCESS_STATUS_CODE = 200
BASIC_AUTHENTICATION_FAILED_STATUS_CODE = 401

_ROOT_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../")

_IRODS_ENCODING = "utf-8"

_IROBOT_DOCKER_BUILD_CONTEXT = _ROOT_DIRECTORY
_IROBOT_DOCKER_BUILD_FILE = os.path.join(_ROOT_DIRECTORY, "Dockerfile")
_IROBOT_IMAGE_NAME = "mercury/irobot-test"
_IROBOT_EXAMPLE_CONFIG_LOCATION = os.path.join(os.path.dirname(os.path.realpath(__file__)), "irobot.conf")


_DUMMY_VALUE = "dummy-value"

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


_HttpStatusPuppetServiceController = DockerisedServiceControllerTypeBuilder(
    repository="mercury/http-status-puppet",
    tag="latest",
    start_log_detector=lambda line: "Starting at" in line,
    start_http_detector=lambda response: response.status_code == 400,
    ports=[8000],
    name="_HttpStatusPuppetServiceController",
    start_tries=1).build()


class StandaloneIrods:
    """
    Standalone iRODS server.
    """
    @property
    def service(self) -> IrodsDockerisedService:
        if self._irods_service is None:
            with self._irods_lock:
                if self._irods_service is None:
                    self._irods_controller = IrodsServiceController()
                    self._irods_service = self._irods_controller.start_service()
        return self._irods_service

    @property
    def configuration_location(self) -> str:
        if self._irods_environment_location is None:
            with self._irods_lock:
                if self._irods_environment_location is None:
                    _, self._irods_environment_location = self._temp_manager.create_temp_file()
                    os.remove(self._irods_environment_location)
            IrodsServiceController.write_connection_settings(self._irods_environment_location, self.service)
        return self._irods_environment_location

    def __init__(self):
        """
        Constructor.
        """
        self._temp_manager = TempManager(default_mkstemp_kwargs=dict(dir=MOUNTABLE_TEMP_DIRECTORY))
        self._irods_lock = Lock()
        self._irods_controller = None
        self._irods_service = None
        self._irods_environment_location = None

    def upload_file(self, contents: str) -> str:
        """
        Uploads the given contents to iRODS and return path to data object (file).
        :param contents: contents to upload
        :return: path to data object
        """
        irods_service = self.service
        file_location = f"/{irods_service.root_user.zone}/{uuid4()}"
        with iRODSSession(host=irods_service.host, port=irods_service.port, user=irods_service.root_user.username,
                          password=irods_service.root_user.password, zone=irods_service.root_user.zone) as session:
            irods_object = session.data_objects.create(file_location)
            with irods_object.open("w") as file:
                file.write(contents.encode(_IRODS_ENCODING))
        return file_location

    def tear_down(self):
        """
        Tears down iRODS if setup.
        """
        with self._irods_lock:
            self._temp_manager.tear_down()
            if self._irods_service is not None:
                self._irods_controller.stop_service(self._irods_service)


class StandaloneAuthenticationServer:
    """
    Standalone authentication server.
    """
    @property
    def service(self) -> DockerisedService:
        if self._basic_authentication_service is None:
            self._basic_authentication_controller = _HttpStatusPuppetServiceController()
            self._basic_authentication_service = self._basic_authentication_controller.start_service()
        return self._basic_authentication_service

    def __init__(self):
        """
        Constructor.
        """
        self._basic_authentication_controller = None
        self._basic_authentication_service = None

    def tear_down(self):
        """
        Tears down authentication server if setup.
        """
        if self._basic_authentication_service is not None:
            self._basic_authentication_controller.stop_service(self._basic_authentication_service)


class StandaloneIrobot:
    """
    Standalone iRobot server.
    """
    _docker_client = docker.from_env()
    _irobot_built = False

    @staticmethod
    def _build_irobot() -> str:
        """
        Builds iRobot Docker image and returns image name.
        :return:
        """
        if not StandaloneIrobot._irobot_built:
            log_generator =_docker_client.api.build(
                path=_IROBOT_DOCKER_BUILD_CONTEXT, dockerfile=_IROBOT_DOCKER_BUILD_FILE,
                tag=_IROBOT_IMAGE_NAME, decode=True)
            for log in log_generator:
                details = log.get("stream", "").strip()
                if len(details) > 0:
                    logger.debug(details)

                    StandaloneIrobot._irobot_built = True

        return _IROBOT_IMAGE_NAME

    @property
    def service(self) -> DockerisedService:
        if self._irobot_service is None:
            basic_authentication_url = f"{self.authentication_server.service.name}:" \
                                       f"{list(self.authentication_server.service.ports.keys())[0]}/" \
                                       f"{BASIC_AUTHENTICATION_SUCCESS_STATUS_CODE}"
            configuration_location = self.create_configuration(basic_authentication_url)
            self._irobot_service = self.start_server(configuration_location, {
                self.authentication_server.service.name: self.authentication_server.service.container_id})
        return self._irobot_service

    @property
    def irobot_url(self) -> str:
        return f"http://{self.service.host}:{self.service.port}"

    def __init__(self, authentication_server: StandaloneAuthenticationServer, irods: StandaloneIrods):
        """
        Constructor.
        :param authentication_server: authentication server to user (life-cycle does not become the responsibility of
        this class)
        :param irods: iRODS server (life-cycle does not become the responsibility of this class)
        """
        self.authentication_server = authentication_server
        self.irods = irods
        self._irobot_controller = None
        self._irobot_service = None
        self._temp_manager = TempManager(default_mkstemp_kwargs=dict(dir=MOUNTABLE_TEMP_DIRECTORY))

    def tear_down(self):
        """
        Tears down iRobot if setup.
        """
        if self._irobot_service is not None:
            self._irobot_controller.stop_service(self._irobot_service)
        self._temp_manager.tear_down()

    def request_data(self, data_object_path: str, irobot_url: str=None) -> Optional[str]:
        """
        Request data from iRobot.
        :param data_object_path: path to the data
        :param irobot_url: the base url of iRobot (will use default iRobot instance if not supplied)
        :return: the data
        """
        if irobot_url is None:
            irobot_url = self.irobot_url

        with TemporaryDirectory() as output_directory:
            arguments = ["irobotclient", "--url", irobot_url, "--basic_username", _DUMMY_VALUE, "--basic_password",
                         _DUMMY_VALUE, "--no_index", data_object_path, output_directory]
            # XXX: irobot client does not treat stdout/stderr with respect
            #      (https://github.com/wtsi-hgi/irobot-client/issues/5) so we can bundle them
            completed_process = subprocess.run(arguments, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            logger.info(completed_process.stdout)
            completed_process.check_returncode()

            data_object_location = os.path.join(output_directory, data_object_path.split("/")[-1])

            if not os.path.exists(data_object_location):
                return None

            with open(data_object_location) as file:
                return file.read()

    def create_configuration(self, basic_authentication_url: str) -> str:
        """
        Creates configuration to use iRobot.
        :param basic_authentication_url: URL that provides basic authentication service
        :return: file location of the configuration
        """
        configuration = ConfigParser()
        configuration.read(_IROBOT_EXAMPLE_CONFIG_LOCATION)
        configuration["basic_auth"]["url"] = basic_authentication_url

        _, configuration_location = self._temp_manager.create_temp_file()
        with open(configuration_location, "w") as file:
            configuration.write(file)
        return configuration_location

    def start_server(self, configuration_location: str, extra_links: Dict[str, str]=None) -> DockerisedService:
        """
        Starts an iRobot server against the iRODs singleton.
        :param configuration_location: location of iRobot configuration to use
        :param extra_links: containers that the iRobot container links to
        :return: Dockerised iRobot server
        """
        extra_links = extra_links if extra_links is not None else {}
        self._build_irobot()
        self._irobot_controller = IrobotServiceController()
        irobot_server = self._irobot_controller.start_service(dict(
            volumes={self.irods.configuration_location: dict(bind="/root/.irods/irods_environment.json", mode="ro"),
                     configuration_location: dict(bind="/root/irobot.conf", mode="ro")},
            environment={"IRODS_PASSWORD": self.irods.service.root_user.password},
            links=dict(**{self.irods.service.container_id: self.irods.service.container_id}, **extra_links)))
        return irobot_server


class TestWithIrodsSingleton(unittest.TestCase, metaclass=ABCMeta):
    """
    Tests that share an iRODS instance.
    """
    @classmethod
    def setUpClass(cls):
        cls._standalone_irods = StandaloneIrods()

    @classmethod
    def tearDownClass(cls):
        cls._standalone_irods.tear_down()

    @property
    def irods(self) -> StandaloneIrods:
        return self._standalone_irods


class TestWithIrobot(TestWithIrodsSingleton, metaclass=ABCMeta):
    """
    Tests that uses iRobot.
    """
    def setUp(self):
        self.authentication_server = StandaloneAuthenticationServer()
        self.irobot = StandaloneIrobot(self.authentication_server, self.irods)

    def tearDown(self):
        self.irobot.tear_down()
        self.authentication_server.tear_down()
