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

import logging
import re
from base64 import b64decode
from datetime import datetime
from threading import Lock, Timer
from types import BooleanType, NoneType, StringType

import requests

from irobot.authentication._base import BaseAuthHandler
from irobot.common import type_check_arguments, type_check_return, type_check_return_tuple
from irobot.config.authentication import BasicAuthConfig
from irobot.logging import LogWriter


BASIC_AUTH_RE = re.compile(r"""
    ^Basic \s
    (
        (?: [a-z0-9+/]{4} )*
        (?: [a-z0-9+/]{2}== | [a-z0-9+/]{3}= )?
    )$
""", re.VERBOSE | re.IGNORECASE)

@type_check_return_tuple(StringType, StringType)
@type_check_arguments(auth_header=StringType)
def _parse_auth_header(auth_header):
    """
    Parse the basic authentication authorisation header

    @param   auth_header  Contents of the "Authorization" header (string)
    @return  Tuple of username (string) and password (string)
    """
    match = BASIC_AUTH_RE.match(auth_header)

    if not match:
        raise ValueError("Invalid HTTP basic authentication header")

    return tuple(b64decode(match.group(1)).split(":"))


class HTTPBasicAuthHandler(LogWriter, BaseAuthHandler):
    """ HTTP basic authentication handler """
    @type_check_arguments(config=BasicAuthConfig, logger=(logging.Logger, NoneType))
    def __init__(self, config, logger=None):
        """
        Constructor

        @param   config  HTTP basic authentication configuration
        @param   logger  Logger
        """
        super(HTTPBasicAuthHandler, self).__init__(logger=logger)
        self._config = config

        if self._config.cache():
            self.log(logging.DEBUG, "Creating HTTP basic authentication cache")
            self._cache = {}  # Dict of user (string) : validation time (datetime)
            self._cache_lock = Lock()
            self._schedule_cleanup()

    def __del__(self):
        """ Cancel any running clean up timer on GC """
        if self._config.cache() and self._cleanup_timer.is_alive():
            self._cleanup_timer.cancel()

    def _schedule_cleanup(self):
        """ Initialise and start the clean up timer """
        self._cleanup_timer = Timer(self._config.cache(), self._cleanup)
        self._cleanup_timer.daemon = True
        self._cleanup_timer.start()

    @type_check_return(BooleanType)
    @type_check_arguments(validation_time=datetime)
    def _has_expired(self, validation_time):
        """
        Whether a validation time was longer ago than the cache expiry

        @param   validation_time  Last validated time (UTC datetime)
        @return  Expiry status (boolean)
        """
        age = datetime.utcnow() - validation_time
        return age.total_seconds() > self._config.cache()

    def _cleanup(self):
        """ Clean up expired entries from the cache """
        with self._cache_lock:
            self.log(logging.DEBUG, "Cleaning HTTP basic authentication cache")
            for user, validation_time in self._cache.items():
                if self._has_expired(validation_time):
                    del self._cache[user]

        self._schedule_cleanup()

    @type_check_return(BooleanType)
    @type_check_arguments(user=StringType, password=StringType)
    def _valid_auth_request(self, user, password):
        """
        Make an authentication request to check for validity

        @param   user      Username (string)
        @param   password  Password (string)
        @return  Validation success (boolean)
        """
        r = requests.get(self._config.url(), auth=(user, password))

        if 200 <= r.status_code < 300:
            self.log(logging.DEBUG, "Authenticated user \"%s\"" % user)
            return True

        if r.status_code in [401, 403]:
            self.log(logging.WARNING, "Couldn't authenticate user \"%s\"" % user)
        else:
            r.raise_for_status()

        return False

    @type_check_return(BooleanType)
    @type_check_arguments(auth_header=StringType)
    def validate(self, auth_header):
        """
        Validate the authorisation header

        @param   auth_header  Contents of the "Authorization" header (string)
        @return  Validation success (boolean)
        """
        try:
            user, password = _parse_auth_header(auth_header)

        except ValueError:
            self.log(logging.WARNING, "Couldn't parse HTTP basic authentication header")
            return False

        # Check the cache
        if self._config.cache():
            with self._cache_lock:
                if user in self._cache and not self._has_expired(self._cache[user]):
                    self.log(logging.DEBUG, "Authenticated user \"%s\" from cache" % user)
                    return True

                # Clean up expired users
                if user in self._cache:
                    del self._cache[user]

        if self._valid_auth_request(user, password):
            # Put validated user in the cache
            if self._config.cache():
                with self._cache_lock:
                    self._cache[user] = datetime.utcnow()

            return True

        return False
