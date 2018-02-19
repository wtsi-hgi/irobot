#!/usr/bin/env bash

set -eux -o pipefail

installDirectory="$(mktemp -d)"
cd "${installDirectory}"

apt-get -qq update
apt-get -y --no-install-recommends install \
    curl \
    build-essential \
    libtool \
    libcurl4-openssl-dev \
    cpanminus \
    ca-certificates

cpanm JSON List::AllUtils
curl http://www.digip.org/jansson/releases/jansson-2.10.tar.gz | tar -xz
cd jansson-2.10
./configure
make
make install

cd "${installDirectory}"
curl -L https://github.com/wtsi-npg/baton/releases/download/1.0.0/baton-1.0.0.tar.gz | tar -xz
cd baton-1.0.0
./configure --with-irods
make
make install

apt-get autoremove
apt-get clean
rm -rf /var/lib/apt/lists/*
rm -rf "${installDirectory}"
