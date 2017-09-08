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

from abc import ABCMeta, abstractmethod
from datetime import datetime, timedelta
from typing import Optional


class AuthenticatedUser(object):
    """ Authenticated user """
    def __init__(self, user:str) -> None:
        self._user = user
        self._authenticated = datetime.utcnow()

    @property
    def user(self) -> str:
        return self._user

    @property
    def authenticated(self) -> datetime:
        return self._authenticated

    def valid(self, invalidation_time:Optional[timedelta]) -> bool:
        """
        Whether a user's authentication has been temporally invalidated

        @param   invalidation_time  Cache invalidation duration (timedelta; None for no caching)
        @return  Validity status (boolean)
        """
        age = datetime.utcnow() - self._authenticated
        return age <= (invalidation_time or timedelta(0))


class BaseAuthHandler(metaclass=ABCMeta):
    @abstractmethod
    async def authenticate(self, auth_header:str) -> Optional[AuthenticatedUser]:
        """
        Asynchronously validate the authorisation header

        @param   auth_header  Contents of the "Authorization" header (string)
        @return  Authenticated user (AuthenticatedUser); None on validation failure
        """

    @property
    @abstractmethod
    def www_authenticate(self) -> str:
        """
        Return the HTTP WWW-Authenticate response header value for this
        authentication method

        @return  WWW-Authenticate value (string)
        """
