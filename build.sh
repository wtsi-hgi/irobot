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

get_krb_realm() {
  # Extract Kerberos realm from /etc/krb5.conf
  (awk 'BEGIN { sec = 0 }
        /\[.*\]/ { sec = 0 }
        /\[libdefaults\]/ { sec = 1 }
        { if (sec) print $0 }' \
  | sed 's/#.*//' \
  | awk '/default_realm/ { print $3 }') \
  < /etc/krb5.conf
}

get_password() {
  # Prompt for user password
  local user="$1"
  local password

  read -srp "Enter password for ${user}: " password
  echo "$password"
}

create_keytab() {
  # Create a new Kerberos keytab file for user principal
  # TODO Get encryption methods from Kerberos configuration
  local user="$1"
  local password="$2"
  local krb_realm="$3"
  local keytab="${user}.keytab"

  local ktutil_script="$(cat <<-EOF
	addent -password -p ${user}@${krb_realm} -k 1 -e arcfour-hmac-md5
	${password}
	addent -password -p ${user}@${krb_realm} -k 1 -e aes256-cts
	${password}
	wkt ${keytab}
	quit
	EOF
  )"

  rm -f "${keytab}"
  ktutil < <(echo "${ktutil_script}") > /dev/null
  echo "${keytab}"
}

create_irods_env() {
  # Create irods_environment.json from template for user
  local user="$1"
  local irods_env="irods_environment.json-${user}"

  export user
  envsubst < irods_environment.json.template > "${irods_env}"

  echo "${irods_env}"
}

create_dockerfile() {
  # Create Dockerfile from template for user
  local user="$1"
  local password="$2"
  local krb_realm="$3"
  local dockerfile="Dockerfile-${user}"

  export user
  export password
  export krb_realm
  export gid="$(id -g "${user}")"
  export group="$(id -gn "${user}")"
  export uid="$(id -u "${user}")"
  export irods_env="$(create_irods_env "${user}")"
  export keytab="$(create_keytab "${user}" "${password}" "${krb_realm}")"
  envsubst < Dockerfile.template > "${dockerfile}"
  
  echo "${dockerfile}"
}

main() {
  local user="$1"
  local password="$(get_password "${user}")"
  local krb_realm="$(get_krb_realm)"

  local dockerfile="$(create_dockerfile "${user}" "${password}" "${krb_realm}")"

  docker build -t "hgi/irobot:${user}" -f "${dockerfile}" .
}

main "${1:-$(whoami)}"
