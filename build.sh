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

declare -a CLEANUP

trim() {
  # Trim whitespace
  awk '{ $1 = $1; print }'
}

new_working_file() {
  local filename="$1"

  echo "${filename}"
  CLEANUP=(${CLEANUP[@]} ${filename})
}

get_krb_libdefaults() {
  # Remove comments and extract libdefaults section from /etc/krb5.conf
  (sed 's/#.*//' \
  | awk 'BEGIN { libdefaults = 0 }
         /\[.*\]/ { libdefaults = 0 }
         /\[libdefaults\]/ { libdefaults = 1 }
         { if (libdefaults) print $0 }') \
  < /etc/krb5.conf
}

get_krb_realm() {
  # Extract Kerberos realm
  get_krb_libdefaults \
  | awk -F'=' '/default_realm/ { print $2 }' \
  | trim
}

get_krb_ciphers() {
  # Extract permitted Kerberos ciphers
  get_krb_libdefaults \
  | awk -F'=' '/permitted_enctypes/ { print $2 }' \
  | trim
}

get_password() {
  # Prompt for user password
  local user="$1"
  local password

  read -srp "Enter password for ${user}: " password
  echo "$password"
}

create_ktutil_script() {
  # Create the ktutil script that creates the Kerberos keytab
  local user="$1"
  local password="$2"
  local krb_realm="$3"
  local keytab="$4"

  for cipher in $(get_krb_ciphers); do
    echo "addent -password -p ${user}@${krb_realm} -k 1 -e ${cipher}"
    echo "${password}"
  done

  echo "wkt ${keytab}"
  echo "quit"
}

create_keytab() {
  # Create a new Kerberos keytab file for user principal
  local user="$1"
  local password="$2"
  local krb_realm="$3"
  local keytab="${user}.keytab"

  rm -f "${keytab}"
  ktutil < <(create_ktutil_script "${user}" "${password}" "${krb_realm}" "${keytab}") > /dev/null
  new_working_file "${keytab}"
}

create_irods_env() {
  # Create irods_environment.json from template for user
  local user="$1"
  local irods_env="irods_environment.json-${user}"

  export user
  envsubst < irods_environment.json.template > "${irods_env}"

  new_working_file "${irods_env}"
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
  
  new_working_file "${dockerfile}"
}

main() {
  local user="$1"
  local password="$(get_password "${user}")"
  local krb_realm="$(get_krb_realm)"

  # We can't use process substitution because the Dockerfile needs to be
  # within the build path, which can't work with named pipes
  local dockerfile="$(create_dockerfile "${user}" "${password}" "${krb_realm}")"
  docker build -t "hgi/irobot:${user}" -f "${dockerfile}" .

  # Delete working files
  rm -f "${CLEANUP[@]}"
}

main "${1:-$(whoami)}"
