#!/bin/bash

set -eu -o pipefail

USER="${1:-$(whoami)}"

docker run -v /etc/krb5.conf:/etc/krb5.conf \
           -it "irods-kerberos-test:${USER}" \
           /bin/bash
