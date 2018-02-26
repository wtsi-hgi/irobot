import logging
import os
import subprocess
import tempfile
import unittest
from abc import ABCMeta
from configparser import ConfigParser
from tempfile import TemporaryDirectory
from threading import Lock
from typing import Dict
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


class TestWithIrodsSingleton(unittest.TestCase, metaclass=ABCMeta):
    """
    Tests that share an iRODS instance.
    """
    @staticmethod
    def upload_file(irods: IrodsDockerisedService, contents: str) -> str:
        file_location = f"/{irods.root_user.zone}/{uuid4()}"
        with iRODSSession(host=irods.host, port=irods.port, user=irods.root_user.username,
                          password=irods.root_user.password, zone=irods.root_user.zone) as session:
            irods_object = session.data_objects.create(file_location)
            with irods_object.open("w") as file:
                file.write(contents.encode(_IRODS_ENCODING))
        return file_location

    @classmethod
    def setUpClass(cls):
        cls._temp_manager = TempManager(default_mkstemp_kwargs=dict(dir=MOUNTABLE_TEMP_DIRECTORY))
        cls._irods_lock = Lock()
        cls._irods_controller = None
        cls._irods_service = None
        cls._irods_environment_location = None

    @classmethod
    def tearDownClass(cls):
        with cls._irods_lock:
            cls._temp_manager.tear_down()
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

    @classmethod
    def get_irods_environment_json_location(cls):
        if cls._irods_environment_location is None:
            with cls._irods_lock:
                if cls._irods_environment_location is None:
                    _, cls._irods_environment_location = cls._temp_manager.create_temp_file()
                    os.remove(cls._irods_environment_location)
            IrodsServiceController.write_connection_settings(cls._irods_environment_location, cls.get_irods())
        return cls._irods_environment_location


class TestWithIrobot(TestWithIrodsSingleton, metaclass=ABCMeta):
    """
    Tests that uses iRobot.
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

    @property
    def irods(self) -> IrodsDockerisedService:
        return self.get_irods()

    @property
    def irods_environment_json_location(self):
        return self.get_irods_environment_json_location()

    @property
    def irobot(self) -> DockerisedService:
        if self._irobot_service is None:
            basic_authentication_url = f"{self.basic_authentication_server.name}:" \
                                       f"{list(self.basic_authentication_server.ports.keys())[0]}/" \
                                       f"{BASIC_AUTHENTICATION_SUCCESS_STATUS_CODE}"
            configuration_location = self.create_irobot_configuration(basic_authentication_url)
            self._irobot_service = self.start_irobot_server(configuration_location, {
                self.basic_authentication_server.name: self.basic_authentication_server.container_id})
        return self._irobot_service

    @property
    def irobot_url(self) -> str:
        return f"http://{self.irobot.host}:{self.irobot.port}"

    @property
    def basic_authentication_server(self) -> DockerisedService:
        if self._basic_authentication_service is None:
            self._basic_authentication_controller = _HttpStatusPuppetServiceController()
            self._basic_authentication_service = self._basic_authentication_controller.start_service()
        return self._basic_authentication_service

    def setUp(self):
        self._irobot_controller = None
        self._irobot_service = None
        self._basic_authentication_controller = None
        self._basic_authentication_service = None
        self._temp_manager = TempManager(default_mkstemp_kwargs=dict(dir=MOUNTABLE_TEMP_DIRECTORY))

    def tearDown(self):
        if self._irobot_service is not None:
            self._irobot_controller.stop_service(self._irobot_service)
        if self._basic_authentication_service is not None:
            self._basic_authentication_controller.stop_service(self._basic_authentication_service)
        self._temp_manager.tear_down()

    def upload_to_irods(self, contents: str) -> str:
        """
        Uploads the given content to iRODS as a data object.
        :param contents: the contents of the data object that will be created
        :return:
        """
        return TestWithIrodsSingleton.upload_file(self.irods, contents)

    def request_data(self, data_object_path: str) -> str:
        """
        Request data from iRobot.
        :param data_object_path: path to the data
        :return: the data
        """
        with TemporaryDirectory() as output_file:
            arguments = ["irobotclient", "--url", self.irobot_url, "--force", "--basic_username", _DUMMY_VALUE,
                         "--basic_password", _DUMMY_VALUE, data_object_path, output_file]

            print(" ".join(arguments))
            try:
                subprocess.check_output(arguments)
            except subprocess.CalledProcessError as e:
                print(e)

    def start_irobot_server(self, configuration_location: str, extra_links: Dict[str, str]=None) -> DockerisedService:
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
            volumes={self.irods_environment_json_location: dict(bind="/root/.irods/irods_environment.json", mode="ro"),
                     configuration_location: dict(bind="/root/irobot.conf", mode="ro")},
            environment={"IRODS_PASSWORD": self.irods.root_user.password},
            links=dict(**{self.irods.container_id: self.irods.container_id}, **extra_links)))
        return irobot_server

    def create_irobot_configuration(self, basic_authentication_url: str) -> str:
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
