#!/usr/bin/env bash

set -eu -o pipefail

SCRIPT_DIRECTORY="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

authenticationScheme=$(cat ~/.irods/irods_environment.json | jq -r '.["irods_authentication_scheme"]')

case "${authenticationScheme}" in
    native)
        >&2 echo "Setting up for native authenication..."
        "${SCRIPT_DIRECTORY}/setup-native.sh"
        ;;
    KRB)
        >&2 echo "Setting up for kerberos authenication..."
        "${SCRIPT_DIRECTORY}/setup-kerberos.sh"
        ;;
    *)
        >&2 echo "Unsupported authentication scheme: ${authenticationScheme}"
        exit 1
        ;;
esac

python3.6 -OOm irobot.main
