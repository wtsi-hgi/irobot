#!/bin/bash

set -eu -o pipefail

USER="${1:-$(whoami)}"

docker run -v /etc/krb5.conf:/etc/krb5.conf \
           -v $(pwd)/irods_environment.json:/home/${USER}/.irods/irods_environment.json \
           -it "irods-kerberos-test:${USER}" \
           /bin/bash
