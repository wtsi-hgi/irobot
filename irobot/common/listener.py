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

from datetime import datetime
from inspect import getargspec, ismethod
from types import FunctionType, MethodType

from irobot.common import type_check, type_check_return


def _check_listener(listener):
    """
    Check listener is a function or method with one argument (or two,
    for methods, to include self), variable and keyword arguments

    @param   listener  Potential listener
    """
    # Check we've got a function or method
    type_check(listener, FunctionType, MethodType)

    # Check the argument signature
    if __debug__:
        argspec = getargspec(listener)

        if len(argspec.args) != (2 if ismethod(listener) else 1) \
        or argspec.varargs is None \
        or argspec.keywords is None:
            raise TypeError("Listener should accept a timestamp, varargs and keywords")


@type_check_return(datetime)
def _broadcast_time():
    """
    Broadcast time

    @return  Current UTC time (datetime)
    """
    return datetime.utcnow()


class Listener(object):
    """ Listener base class """
    def __init__(self):
        self._listeners = []

    def add_listener(self, listener):
        """
        Add a listener for broadcast messages

        @param   listener  Listener (function taking timestamp, *args and **kwargs)
        """
        _check_listener(listener)
        self._listeners.append(listener)

    def broadcast(self, *args, **kwargs):
        """ Broadcast a message to all the listeners """
        timestamp = _broadcast_time()
        for listener in self._listeners:
            listener(timestamp, *args, **kwargs)
