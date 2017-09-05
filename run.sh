#!/bin/bash

# Copyright (c) 2017 Genome Research Ltd.
# 
# Author: Christopher Harrison <ch12@sanger.ac.uk>
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

set -eu -o pipefail

USER="${1:-$(whoami)}"

docker run -v /etc/krb5.conf:/etc/krb5.conf \
           -it "hgi/irobot:${USER}" \
           /bin/bash
