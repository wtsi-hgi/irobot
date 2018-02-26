#!/usr/bin/env bash

set -eu -o pipefail

if [[ -n ${IRODS_PASSWORD+x} ]]; then
    >&2 echo "IRODS_PASSWORD supplied - using it to generate .irodsA file"
    rm ~/.irods/.irodsA
    iinit "${IRODS_PASSWORD}"
fi
