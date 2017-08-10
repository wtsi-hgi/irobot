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

from datetime import datetime, timedelta
from json import JSONEncoder
from numbers import Number
from typing import Any, Sequence, Text

from irobot.config._tree_builder import Configuration, ConfigValue


class ConfigJSONEncoder(JSONEncoder):
    """ Encode configuration trees into JSON """
    def default(self, o:Any) -> Any:
        if isinstance(o, Configuration):
            return {k: o._leaves[k] for k in o}

        if isinstance(o, ConfigValue):
            raw = o._raw_value
            computed = o._value

            if isinstance(computed, (Number, Sequence, Text, bool)):
                # Already JSON serialisable
                return computed

            if isinstance(computed, (datetime, timedelta)):
                # Meaningful string representation
                return str(computed)

            if computed is None:
                if raw.lower() not in ["", "none", "null"]:
                    # Meaningful raw string that is transformed into None
                    return raw

                return None

            # Otherwise just spit out the raw string
            return raw

        # If all else fails
        super().default(o)
