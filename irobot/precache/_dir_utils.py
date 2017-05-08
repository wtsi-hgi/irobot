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

import os
import shutil
from uuid import uuid4


def new_name(precache_path:str) -> str:
    """
    Create a new precache directory path (i.e., just the string), by
    appending the precache base directory to a UUID4 split into 2-byte
    segments (i.e., so each level contains a maximum of 256 directories)

    @param   precache_path  Precache base path (string)
    @return  Precache directory path (string)
    """
    segments = map(lambda x: "".join(x), zip(*[iter(uuid4().hex)] * 2))
    return os.path.join(precache_path, *segments)


def create(precache_dir:str) -> None:
    """
    Create a given precache directory on the filesystem (mkdir -p)

    @param   precache_dir  Full precache directory
    @note    Use with _new_precache_dir separately so the tracking DB
             can check for collisions
    @note    The directory is fully accessible to the user and only
             readable by the group
    """
    os.makedirs(precache_dir, mode=0o750)


def delete(precache_dir:str) -> None:
    """
    Delete the top-level precache directory and its contents from the
    filesystem

    @param   precache_dir  Full precache directory
    @note    e.g., if deleting /foo/bar/quux, only quux will be removed
    """
    shutil.rmtree(precache_dir)
