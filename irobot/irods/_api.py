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

import json
import os
import subprocess
from collections import Iterable
from tempfile import TemporaryFile
from typing import Sequence, TextIO, Tuple, Union


def _invoke(command:Union[str, Sequence[str]], stdin:Union[None, int, str, TextIO] = None, shell:bool = False) -> Tuple[int, str, str]:
    """
    Run a command with the provided arguments

    @note    Blocking
    @note    This is only intended for invoking commands with short(ish)
             output (i.e., trading the properties of streams for
             convenience)

    @param   command  Command to run (string/s)
    @param   stdin    Standard input (None/int/string/file)
    @param   shell    Execute within shell (boolean)
    @return  Exit code, stdout and stderr (tuple of int, string, string)
    """
    # stdin as string...
    if isinstance(stdin, str):
        with TemporaryFile(mode="w+t") as stdin_file:
            stdin_file.write(stdin)
            stdin_file.flush()
            stdin_file.seek(0)

            return _invoke(command, stdin_file, shell)

    # ...otherwise
    with TemporaryFile(mode="w+t") as stdout, TemporaryFile(mode="w+t") as stderr:
        exit_code = subprocess.call(command, stdin=stdin,
                                             stdout=stdout,
                                             stderr=stderr,
                                             shell=shell)
        stdout.flush()
        stdout.seek(0)
        out = stdout.read()
        stderr.flush()
        stderr.seek(0)
        err = stderr.read()

    return exit_code, out, err


def ils(irods_path:str) -> None:
    """
    Wrapper for ils

    @param   irods_path  Path to data object on iRODS (string)
    """
    command = ["ils", irods_path]

    exit_code, stdout, stderr = _invoke(command)
    if exit_code:
        raise subprocess.CalledProcessError(returncode=exit_code,
                                            cmd=" ".join(command),
                                            output=(stdout, stderr))

def iget(irods_path:str, local_path:str) -> None:
    """
    Wrapper for iget

    @param   irods_path  Path to data object on iRODS (string)
    @param   local_path  Local filesystem target file (string)
    """
    command = ["iget", "-f", irods_path, local_path]

    exit_code, stdout, stderr = _invoke(command)
    if exit_code:
        raise subprocess.CalledProcessError(returncode=exit_code,
                                            cmd=" ".join(command),
                                            output=(stdout, stderr))

def baton(irods_path:str) -> None:
    """
    Wrapper for baton-list

    @param   irods_path  Path to data object on iRODS (string)
    @return  Deserialised JSON (various)
    """
    baton_json = "{{\"collection\":\"{}\",\"data_object\":\"{}\"}}".format(*os.path.split(irods_path))
    command = ["baton-list", "--avu", "--size", "--checksum", "--acl", "--timestamp"]

    exit_code, stdout, stderr = _invoke(command, baton_json)
    if exit_code:
        raise subprocess.CalledProcessError(returncode=exit_code,
                                            cmd=" ".join(command),
                                            output=(stdout, stderr))
    return json.loads(stdout)
