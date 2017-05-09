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
from typing import Dict, List


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


class Metadata(object):
    """
    Everything you wanted to know about metadata, but were too afraid to ask...

    iRODS filesystem metadata:
    * checksum  MD5 checksum reported by iRODS; we also calculate this
                locally and use it as a sanity check
    * size      File size in bytes
    * created   Creation timestamp (UTC)
    * modified  Last modified timestamp (UTC)

    iRODS AVU metadata:
    * avus      Array of dictionaries with "attribute", "value" and
                (optionally) "units" keys
    """
    def __init__(self, checksum:str, size:int, created:datetime, modified:datetime, avus:List[Dict]) -> None:
        self.checksum = checksum
        self.size = size
        self.created = created
        self.modified = modified
        self.avus = avus


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
                        base["avus"])

class MetadataJSONEncoder(JSONEncoder):
    """ Encode a Metadata object into JSON """
    def default(self, m:Metadata) -> Dict:
        return {
            "checksum": m.checksum,
            "size": m.size,
            "timestamps": [
                {"created": m.created.strftime(_IRODS_TIMESTAMP_FORMAT)},
                {"modified": m.modified.strftime(_IRODS_TIMESTAMP_FORMAT)}
            ],
            "avus": m.avus
        }
