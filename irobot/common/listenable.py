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
from datetime import datetime
from typing import Callable, Dict, List, Tuple, Type, Union

# FIXME? No facility is provided for annotating var- and keyword
# arguments, so we suck it up with a Tuple and Dict, respectively
_BaseArgSignature = [datetime, Tuple, Dict]
_ListenerFunction = Callable[_BaseArgSignature, None]
_ListenerMethod = Callable[[Type] + _BaseArgSignature, None]
_ListenerCallable = Union[_ListenerFunction, _ListenerMethod]


def _broadcast_time() -> datetime:
    """
    Broadcast time

    @return  Current UTC time (datetime)
    """
    return datetime.utcnow()


class Listenable(object):
    """ Listenable base class """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._listeners: List[_ListenerCallable] = []

    def add_listener(self, listener: _ListenerCallable) -> None:
        """
        Add a listener for broadcast messages

        @param   listener  Listener (function taking timestamp, *args and **kwargs)
        """
        self._listeners.append(listener)

    def broadcast(self, *args, **kwargs) -> None:
        """ Broadcast a message to all the listeners """
        timestamp = _broadcast_time()
        for listener in self._listeners:
            try:
                listener(timestamp, *args, **kwargs)
            except Exception as e:
                # Don't let one listener ruin it for everyone
                # FIXME: I don't know what the correct logger to use is - feels like it should be a module level one?
                logging.error(e)
