#!/usr/bin/env bash

set -eu -o pipefail

SCRIPT_DIRECTORY="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

authenticationScheme=$(cat ~/.irods/irods_environment.json | jq -r '.["irods_authentication_scheme"]')

case "${authenticationScheme}" in
    native)
        >&2 echo "Setting up for native authentication..."
        "${SCRIPT_DIRECTORY}/setup-native.sh"
        ;;
    KRB)
        >&2 echo "Setting up for kerberos authentication..."
        if [[ IRODS_KERBEROS_SUPPORT -ne 1 ]]; then
            >&2 echo "This image was not build with Kerberos support enabled. Build with IRODS_KERBEROS_SUPPORT set" \
                     "to 1 to enable Kerberos."
            exit 1
        fi
        "${SCRIPT_DIRECTORY}/setup-kerberos.sh"
        ;;
    *)
        >&2 echo "Unsupported authentication scheme: ${authenticationScheme}"
        exit 1
        ;;
esac

# TODO: Handle different CMD
python3.6 -OOm irobot.main
