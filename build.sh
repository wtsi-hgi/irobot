#!/bin/bash

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
  read -s -p "Enter password for ${user}: " password
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

  rm -f ${keytab}
  ktutil < <(echo "${ktutil_script}") > /dev/null
  echo "${keytab}"
}

create_dockerfile() {
  # Create Dockerfile from template for user
  export user="$1"
  export keytab="$2"
  export krb_realm="$3"
  export gid="$(id -g ${user})"
  export group="$(id -gn ${user})"
  export uid="$(id -u ${user})"
  envsubst < Dockerfile.template
}

main() {
  local user="$1"
  local password="$(get_password $user)"
  local krb_realm="$(get_krb_realm)"

  local keytab="$(create_keytab "${user}" "${password}" "${krb_realm}")"

  docker build -t "irods-kerberos-test:${user}" -f <(create_dockerfile "${user}" "${keytab}" "${krb_realm}")
}

main ${1:-$(whoami)}
