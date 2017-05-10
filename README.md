# iRobot

<!-- TODO Change to master branch on release -->
[![Build Status](https://travis-ci.org/wtsi-hgi/irobot.svg?branch=develop)](https://travis-ci.org/wtsi-hgi/irobot)
[![Test Coverage](https://codecov.io/gh/wtsi-hgi/irobot/branch/develop/graph/badge.svg)](https://codecov.io/gh/wtsi-hgi/irobot)

iRODS data brokerage service: Data objects from iRODS are requested by
an authenticated agent, via HTTP, which are then staged on local disk
before being sent out as a response. The service also acts as a
precache, to presumptively seed upstream systems with data, as well as
managing a connection pool to iRODS.

## Work in Progress

- [x] Configuration parsing
  - [x] Precache
  - [x] iRODS
  - [x] HTTP API
  - [x] Authentication
    - [x] HTTP Basic
    - [x] Arvados
  - [x] Logging
- [x] Logging
- [x] iRODS interface
  - [x] Metadata model
  - [x] iCommand and baton wrappers
- [ ] Precache
  - [x] Tracking database
  - [x] Checksummer
  - [x] Filesystem directory handlers
  - [ ] Precache entity
  - [ ] Precache manager
- [x] Authentication handlers
  - [x] HTTP Basic
  - [x] Arvados
- [ ] HTTP interface
  - [ ] ...
- [ ] Installation/containerisation
  - [x] Base system
  - [x] Kerberos support
  - [ ] iRobot
- [ ] Testing
  - [x] Unit testing
  - [ ] Integration testing
  - [ ] User acceptance testing
- [x] Documentation

## Installation

iRobot is fully containerised, using Docker. The container image can be
built using the `build.sh` script:

    build.sh AUTH_METHOD [USER] 

Build script requirements:

* Bash (4, or newer)
* Docker
* GNU gettext
* Awk
* Sed

If using Kerberos authentication, the Kerberos client packages also need
to be available on the Docker host. Additionally, it is expected that
the host's `/etc/krb5.conf` would be bind mounted into the container at
runtime; this configuration file is also used at build-time to determine
the default Kerberos realm and permitted encryption algorithms.

Before running the build script, the `irods_environment.json.template`
file needs to be created, based on `irods_environment.json.template.sample`.
In which, the `irods_host`, `irods_port`, `irods_zone_name` and,
potentially, `irods_cwd` and `irods_home` values need to be set
appropriately. The `${user}` tags in the template file will be replaced
with `USER` by the build script.

The `AUTH_METHOD` can be either `native` (`nat`) or `kerberos` (`krb`).
If the `USER` is omitted, then the current login is used. The script
then builds an image named `hgi/irobot`, with the `USER` given as its
tag.

To launch the container:

    docker run -v /path/to/your/precache/directory:/precache \
               -v /etc/krb5.conf:/etc/krb5.conf \
               -v /path/to/your/irobot.conf:/home/USER/irobot.conf \
               -p 5000:5000 \
               hgi/irobot:USER

(Note that bind mounting `/etc/krb5.conf` is only necessary when using
Kerberos authentication. A `cron` job runs in the Kerberos container to
renew credentials with the KDC periodically; if the container is down
for any significant amount of time, this may fail and you'll have to
rebuild the image.)

## Configuration

The `irobot.conf` configuration is not copied into the image and ought
to be bind mounted at runtime, into `USER`'s home directory. This allows
you to make configuration changes without rebuilding. An example
configuration can be found in `irobot.conf.sample`.

### Precache Policy

* **`location`** The directory that stores the contents of the precache.
  If using the containerised application, this should be set to the
  location of the bind mounted volume within the container
  (conventionally `/precache`).

* **`index`** The precache tracking database filename. If a single
  filename component is given, then it is assumed to reside within the
  precache location; otherwise it will be stored at the specified
  location. (This probably won't need to be changed.)

* **`size`** The maximum size of the precache. It can be set to
  `unlimited`, where it is allowed to grow indefinitely (until the disk
  fills), or to a defined limit. Upon reaching the limit, the oldest
  files (in terms of access time) are removed.

  The limit should be the number of bytes, optionally suffixed with `B`;
  decimal (base 1000: `k`, `M`, `G`, `T`) or binary (base 1024: `ki`,
  `Mi`, `Gi`, `Ti`) multiplier prefixes may also be used with the `B`
  suffix.

  If the precache size limit is not large enough to accommodate a
  requested file, the request will fail.

* **`expiry`** The maximum age (in terms of access time) of files in the
  precache. It can be set to `unlimited`, so that files never expire, or
  to a defined limit. Upon reaching the limit, files are removed.

  The limit should be suffixed with any of the following units: `h`
  (`hour`), `d` (`day`), `w` (`week`) or `y` (`year`); fully spelt units
  may be pluralised. Year units will be relative (e.g., `1 year` means
  "delete a file on the anniversary of its last access"), while the
  others will be absolute.

* **`chunk_size`** The size of file blocks for MD5 checksums. The size
  should be the number of bytes, optionally suffixed with `B`; decimal
  (base 1000: `k`, `M`, `G`, `T`) or binary (base 1024: `ki`, `Mi`,
  `Gi`, `Ti`) multiplier prefixes may also be used with the `B` suffix.

### iRODS

* **`max_connections`** The maximum number of concurrent connections
  allowed to iRODS.

### HTTP API

* **`bind_address`** The IPv4 address to which the HTTP API server
  should bind. When containerised, this can be set to `127.0.0.1`.

* **`listen`** The network port to which the HTTP API server should
  listen for requests. When containerised, this port should be exposed
  and mapped to a host port with the `-p` option to `docker run`.

* **`timeout`** The timeout for responses, which can be set to
  `unlimited` to keep the connection alive until the response content is
  available (not recommended), or to a specific number of milliseconds
  (with an optional `ms` suffix) or seconds (with a mandatory `s`
  suffix).

* **`authentication`** The available authentication handlers, which is a
  comma-separated list of at least one of `basic` and `arvados`, in any
  order. Note that the corresponding authentication section (eponymously
  named with an `_auth` suffix) must appear in the configuration file
  for each specified authentication handler.

  Note that the order is important; once a handler has successfully
  authenticated a request, the subsequent handlers will not be called
  for that request. This allows authentication methods to be
  prioritised. While not recommended, if no authentication is required,
  `basic` can be used alone, configured to point at a dummy webserver
  that always responds with a `200 OK` status.

Note that it is recommended that the HTTP API is *only* served over TLS
(e.g., using a reverse proxy), to avoid authentication credentials being
exposed as plain-text over an unencrypted connection.

### HTTP Basic Authentication

This is only needed if using HTTP basic authentication.

* **`url`** The basic authentication handler will make a request to the
  resource at this URL, forwarding the credentials received in the
  response in attempt to authenticate them (i.e., checking for a
  `200 OK` response from this URL).

  Note that it is recommended that an authentication URL served over TLS
  is used, to avoid the forwarded basic authentication credentials being
  exposed as plain-text over an unencrypted connection.

* **`cache`** How long an authenticated response from the authentication
  URL should be cached by the handler. It can be set to "never", to
  authenticate every request, or a positive, numeric time suffixed with
  either `s` (`sec` or `second`) or `m` (`min` or `minute`), where spelt
  units may be pluralised.

### Arvados Authentication

This is only needed if using Arvados authentication.

* **`api_host`** The Arvados authentication handler will make a request
  to the Arvados API host at this hostname with the credentials received
  in the response in attempt to authenticate them.

* **`api_version`** The version of the Arvados API served by the
  specified Arvados API host. (This probably won't need to be changed.)

* **`cache`** How long an authenticated response from the Arvados API
  host should be cached by the handler. It can be set to "never", to
  authenticate every request, or a positive, numeric time suffixed with
  either `s` (`sec` or `second`) or `m` (`min` or `minute`), where spelt
  units may be pluralised.

### Logging

Log messages are tab-delimited timestamp (ISO8601 UTC), level and
message records.

* **`output`** The destination of all log messages, which should be set
  to either `STDERR` to stream to standard error, otherwise it will be
  considered as a filename for appendage. Note that if logging is sent
  to file while containerised, that file should be within a bind mounted
  directory so it can be accessed and persist.

* **`level`** The minimum level of logging output by iRobot, which can
  be set to any of the following in decreasing granularity (in terms of
  output): `debug`, `info`, `warning`, `error` or `critical`.

## API

Note that, due to iRODS data objects' full paths starting with a slash,
HTTP resource addressing makes productive use of the query string,
rather than embedding paths into the URL. If the requested data object
does not exist in iRODS, then a `404 Not Found` response will be
returned.

### Authentication

All HTTP requests must include the `Authorization` header with a value
that can be handled by any one of the configured authentication
handlers. That is:

* `Basic <payload>`, where the payload is the Base64 encoding of
  `username:password` for basic HTTP authentication.

* `Arvados <payload>`, where the payload is an API token supplied by
  Arvados for Arvados authentication.

If the respective authentication handler cannot authenticate the payload
it's given (or no `Authorization` header exists), a `401 Unauthorized`
response will be returned. If the payload can be authenticated, but the
user does not have the necessary access to the requested resource, a
`403 Forbidden` response will be returned.

### Precache Failure

If the constraints of the precache are impossible to satisfy (e.g.,
trying to fetch a data object that's bigger than the precache), then a
`507 Insufficient Storage` response will be returned.

### `/data/?do=<iRODS Data Object Path>`

#### `GET`

Fetch the data object from iRODS as `application/octet-stream`. This
method accepts range requests to return requested byte ranges of the
data object.

 Status | Semantics
:------:|:--------------------------------------------------------------
 200    | Return data object
 202    | Data object still being fetched from iRODS
 206    | Return ranges of data object

Note that if iRobot has yet to fetch the data object (or any specified
ranges thereof), a `202 Accepted` response will be returned with the
`text/plain` content of the estimated finish time (per ISO8601), or
empty content if this estimate cannot be calculated. A data object can
be forcibly refetched by sending the `Cache-Control: no-cache` request
header; although, if none of the filesystem metadata have changed (file
size, checksum, timestamps), then no refetch will be performed.

#### `POST`

Seed the precache with the data object and its metadata.

 Status | Semantics
:------:|:--------------------------------------------------------------
 202    | Seed the precache with data object

Note that if the data object and its metadata are already cached or
partially cached, this action will forcibly refetch them.

### `/metadata/?do=<iRODS Data Object Path>`

#### `GET`

Fetch the iRODS AVU and filesystem metadata of the requested data object
as `application/json`.

 Status | Semantics
:------:|:--------------------------------------------------------------
 200    | Return iRODS metadata of data object

Note that the metadata for the requested data object will be cached from
the first fetch. To forcibly refetch the metadata (and update the cache)
the `Cache-Control: no-cache` request header can be sent; if any of the
filesystem metadata have changed (file size, checksum, timestamps), this
will trigger a refetching of the data.

### `/checksum/?do=<iRODS Data Object Path>`

#### `GET`

Fetch the MD5 checksum of the requested data object, as computed by
iRobot, as `text/plain`. This method accepts range requests to return
the MD5 checksums of requested byte ranges of the data object.

 Status | Semantics
:------:|:--------------------------------------------------------------
 200    | Return MD5 checksum of entire data object
 202    | MD5 checksum calculation pending
 206    | Return MD5 checksums of ranges of data object

Note that if iRobot has yet to compute the MD5 sum for the data object,
a `202 Accepted` response will be returned with the `text/plain` content
of the estimated finish time (per ISO8601), or empty content if this
estimate cannot be calculated. MD5 checksums of range requests will be
chunked according to the precache chunk size.
