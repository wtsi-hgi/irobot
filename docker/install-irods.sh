#!/usr/bin/env bash

set -eu -o pipefail

installDirectory="$(mktemp -d)"
cd "${installDirectory}"

apt-get -qq update
apt-get -y --no-install-recommends install \
    curl \
    software-properties-common \
    libssl-dev \
    libfuse2 \
    jq

add-apt-repository -y ppa:deadsnakes/ppa
apt-get -qq update
apt-get -y --no-install-recommends install \
    python3.6 \
    python3.6-dev
curl https://bootstrap.pypa.io/get-pip.py | python3.6

# Download and install iRODS client, shared objects and development
# headers and Kerberos plugin, if needed
curl -O ftp://ftp.renci.org/pub/irods/releases/4.1.10/ubuntu14/irods-icommands-4.1.10-ubuntu14-x86_64.deb \
     -O ftp://ftp.renci.org/pub/irods/releases/4.1.10/ubuntu14/irods-runtime-4.1.10-ubuntu14-x86_64.deb \
     -O ftp://ftp.renci.org/pub/irods/releases/4.1.10/ubuntu14/irods-dev-4.1.10-ubuntu14-x86_64.deb
dpkg -i irods-icommands-4.1.10-ubuntu14-x86_64.deb \
    irods-runtime-4.1.10-ubuntu14-x86_64.deb \
    irods-dev-4.1.10-ubuntu14-x86_64.deb

# TODO: Optionally install Kerberos packages
apt-get -y --no-install-recommends install \
    python \
    krb5-user \
    libgssapi-krb5-2 \
    libkrb5-dev
curl -O ftp://ftp.renci.org/pub/irods/plugins/irods_auth_plugin_krb/1.4/irods-auth-plugin-krb-1.4-ubuntu14-x86_64.deb
dpkg -i irods-auth-plugin-krb-1.4-ubuntu14-x86_64.deb

mkdir ~/.irods/
touch ~/.irods/irods_environment.json

apt-get autoremove
apt-get clean
rm -rf /var/lib/apt/lists/*
rm -rf "${installDirectory}"
