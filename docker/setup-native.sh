#!/usr/bin/env bash

set -eu -o pipefail

if [[ -f ~/.irods/.irodsA ]]; then
    >&2 echo ".irodsA file already exists"
else
    if [[ -z ${IRODS_PASSWORD+x} ]]; then
        >&2 echo "IRODS_PASSWORD must be defined to use native authentication to generate .irodsA file"
    fi
    iinit "${IRODS_PASSWORD}"
fi
