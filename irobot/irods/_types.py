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

import re
from datetime import datetime
from json import JSONDecoder, JSONEncoder
from typing import Any, Dict, List, NamedTuple, Optional


# iRODS timestamps are of the form "YYYY-MM-DDTHH:MM:SS" and
# (experimentally) always UTC
_IRODS_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S"
_IRODS_TIMESTAMP_RE = re.compile(r"""
    ^
    \d{4} - \d{2} - \d{2}
    T
    \d{2} : \d{2} : \d{2}
    $
""", re.VERBOSE)


class AVU(NamedTuple):
    """
    iRODS AVU (attribute, value, units) tuple
    """
    attribute:str
    value:str
    units:Optional[str] = None


class Metadata(NamedTuple):
    """
    Everything you wanted to know about iRODS metadata, but were too
    afraid to ask...
    """
    # iRODS filesystem metadata
    checksum:str       # MD5 checksum reported by iRODS
    size:int           # File size in bytes
    created:datetime   # Creation timestamp (UTC)
    modified:datetime  # Last modified timestamp (UTC)

    # iRODS AVU metadata
    avus:List[AVU]     # List of AVUs


class MetadataJSONDecoder(JSONDecoder):
    """ Decode baton's JSON output into a Metadata object """
    def decode(self, s:str) -> Metadata:
        base = super().decode(s)

        timestamps = {
            k: datetime.strptime(v, _IRODS_TIMESTAMP_FORMAT)
            for ts in base["timestamps"]
            for k, v in ts.items()
            if _IRODS_TIMESTAMP_RE.match(str(v))
        }

        return Metadata(base["checksum"],
                        base["size"],
                        timestamps["created"],
                        timestamps["modified"],
                        [AVU(**avu) for avu in base["avus"]])

class MetadataJSONEncoder(JSONEncoder):
    """
    Encode a Metadata object into JSON

    Note that this is very specific to Metadata (and AVU) objects
    because json.JSONEncoder will serialise supported types (of which,
    tuple is one; all named tuples are tuples) before delegating to the
    default method, which serialises custom types.
    """
    def default(self, o:Any) -> Any:
        if isinstance(o, datetime):
            return o.strftime(_IRODS_TIMESTAMP_FORMAT)

        if isinstance(o, AVU):
            return {
                "attribute": o.attribute,
                "value": o.value,
                **({"units": o.units} if o.units else {})
            }

        # If all else fails
        super().default(o)

    def encode(self, o:Any) -> str:
        if isinstance(o, Metadata):
            return super().encode({
                "checksum": o.checksum,
                "size": o.size,
                "timestamps": [{"created": o.created}, {"modified": o.modified}],
                "avus": [self.default(avu) for avu in o.avus]
            })

        return super().encode(o)
