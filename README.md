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
  - [ ] Precache manager
    - [x] Garbage collector/cache invalidator
    - [ ] Precache entity
    - [ ] [Request workflow](irobot/precache/README.md)
- [x] Authentication handlers
  - [x] HTTP Basic
  - [x] Arvados
- [ ] HTTP interface
  - [x] Response timeout middleware
  - [x] Authentication middleware
  - [ ] Data object endpoint
    - [ ] `GET` and `HEAD`
    - [ ] `POST`
    - [ ] `DELETE`
  - [ ] Administrative endpoints
    - [x] Common middleware
    - [ ] Status endpoint
    - [ ] Configuration endpoint (is this necessary?...)
    - [ ] Precache manifest endpoint
- [ ] Installation/containerisation
  - [x] Base system
  - [x] Kerberos support
  - [ ] iRobot
- [ ] Testing
  - [ ] Unit testing
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

* **`age_threshold`** If the precache size is limited (using the above),
  then older data may be culled to accommodate newer requests; the age
  threshold defines the minimum age (in terms of access time) data must
  be for it to be forcefully invalidated.

  This option is only relevant if `size` is not `unlimited`, otherwise
  it will be ignored. The threshold can be set to `unlimited` to avoid
  this behaviour (the default, if omitted). Otherwise, its value should
  be numeric suffixed with any of the following units: `h` (`hour`), `d`
  (`day`), `w` (`week`) or `y` (`year`); fully spelt units may be
  pluralised.

  It is recommended that this should be set to `unlimited` or a large
  value, otherwise the precache is at risk of DoS attacks from requests
  that saturate it.

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
  suffix), greater than zero.

  Note that any request that triggers data fetching from iRODS will
  respond, in that first instance, with a `202 Accepted` and never,
  regardless of the timeout setting, wait for the data to be fetched and
  then respond with it under `200 OK`. That is to say, the timeout
  setting is used to cancel unusually long-running operations, so not to
  tie up the API server, and should be set relatively high to indicate
  back to any client that there's something wrong with the iRODS
  gateway.

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

### Gateway Timeout

iRobot essentially acts as an iRODS gateway through this HTTP API. If
any operation takes an overly long time to complete (per the respective
configuration), then a `504 Gateway Timeout` response will be issued.
(This *may* not be due to iRODS, but that will be the most likely
culprit.) If this happens regularly, it may be indicative of a
configuration or networking problem between iRobot and iRODS.

(Note that any client would also, presumably, hang up on an overly
long-running connection.)

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
user (that is, the iRODS account under which iRobot operates) does not
have the necessary access to the requested resource, a `403 Forbidden`
response will be returned.

### Data Object Endpoint

iRobot exposes a single, parametrised endpoint at its root, taking the
iRODS full path (collection name and data object, interspersed with
slash characters) as its parameter. Note that, as the absolute path is
taken as the parameter, the initial slash is assumed to be there so
shouldn't be used in the URL.

That is, for example, for data object `data_object` in collection
`/full/path/to/my`:

```
👍 https://irobot:5000/full/path/to/my/data_object
```
```
❌ https://irobot:5000//full/path/to/my/data_object
```

Any special characters in the iRODS path should be percent encoded.  If
the requested data object does not exist in iRODS, then a `404 Not
Found` response will be returned.

#### `GET` and `HEAD`

##### Response Summary

 Status | Semantics
:------:|:--------------------------------------------------------------
 200    | Return data object
 202    | Data object still being fetched from iRODS; ETA returned, if possible
 206    | Return ranges of data object, with ETA part (if possible) for missing ranges
 304    | Data object matches that expected by client
 401    | Authentication failure
 403    | Access denied to iRobot iRODS user
 404    | No such data object on iRODS
 405    | Method not allowed (only `GET`, `HEAD`, `POST`, `DELETE` and `OPTIONS` are supported)
 406    | Unsupported requested media type
 416    | Invalid range request
 504    | Response timeout
 507    | Precache full

A `HEAD` request can be made to the data object endpoint to facilitate
discovery and status tracking, without the overhead of a full `GET`.
That is, the same actions described below will be invoked on a `HEAD`
request, but only the response headers will be returned.

##### Using the `Accept` Request Header

The `Accept` request header is used productively to fetch an appropriate
representation of the specific data object:

* If it is omitted, or `application/octet-stream` is the primarily
  accepted media type, then the data (or ranges, thereof) for the
  specified data object will be returned, with checksums if available.

* If the primarily accepted media type is
  `application/vnd.irobot.metadata+json`, then a JSON representation of
  the metadata for the specified data object will be returned.

* Otherwise, a `406 Not Acceptable` response will be returned.

##### Client Cache Validity

The response will always include the `ETag` header with its value
corresponding to the MD5 checksum of the data object cached by iRobot.
This will allow the client to verify it is requesting the same version
of the data object that it is expecting.

A client can ensure this programmatically by using the `If-None-Match`
request header, with the given ETag. If the tags match, a `304 Not
Modified` response will be returned; otherwise, a full response will be
returned.

This behaviour will also be true of a range request, so if a client
wishes to fetch a range it doesn't have from a source it's seen before,
then it would either make two requests -- first with the `If-None-Match`
header then the second without -- or a single request without the
`If-None-Match` header, that would need to be analysed by the client.

##### Manual Cache Invalidation

A data object can be forcibly refetched by sending the `Cache-Control:
no-cache` request header. This will delete the currently stored data
object state and refetch it from iRODS if none of the filesystem
metadata have changed (file size, checksum and timestamps); otherwise,
the invalidation will be cancelled.

If the cache control header is used on a metadata request, then the
metadata will be refetched from iRODS. Again, if any of the filesystem
metadata have changed, this will also trigger an invalidation of the
data and its refetching from iRODS.

If another user is requesting data that is manually invalidated by
someone else, their response will be interrupted and cancelled, as the
data will be removed. Data on iRODS shouldn't change often (or at all),
so not protecting against such an event is seen as a justifiable
trade-off.

##### Fetching Data

Fetching of the data supports range requests using the `Accept-Ranges`
request header. If this header is present and the data exists, it will
be returned with a `206 Partial Content` response under the
`multipart/byteranges` media type, where byte ranges in the response
will have the media type `application/octet-stream` and include a
`Content-MD5` if one exists. The ranges may therefore be chunked
differently than requested, so that they align with the precache
checksum chunk size, but the requested range will be fully satisfied.

If the `Accept-Ranges` request header is omitted, then the entirety of
the data will be returned as a `200 OK` response, with media type
`application/octet-stream` and a `Content-MD5` header, if available.

If a range request is not satisfiable due to the request being
out-of-bounds, then a `416 Range Not Satisfiable` response will be
issued. If a request (full or ranged) is valid, but some of the
requested data has yet to be fetched, a `206 Parial Content` multipart
response will be issued that includes as much data as there is currently
available and a final ETA response part; if no data is available (e.g.,
upon initial request), then a `202 Accepted` ETA response will be
issued.

Note that an initial range request (i.e., for data that has yet to be
precached) will still fetch the entirety of the data into the precache;
there is no short-cutting.

##### Precache Saturation

If the constraints of the precache are impossible to satisfy (e.g.,
trying to fetch a data object that's bigger than the precache), then a
`507 Insufficient Storage` response will be returned.

##### ETA Reponses

An ETA response indicates when data may be available. It will have media
type `application/vnd.irobot.eta`. This will have an empty content body
(i.e., content length of 0 bytes) and, if it can be calculated, a
response header `iRobot-ETA` containing an ISO8601 UTC timestamp and an
indication of confidence (in whole seconds) of when the data will be
available. For example:

    iRobot-ETA: 2017-09-25T12:34:56Z+00:00 +/- 123

A client may choose to use this information to inform the rate at which
it reissues requests.

#### `POST`

Seed the precache with the data object, its metadata and calculate
checksums; thus warranting its title of "precache"!

 Status | Semantics
:------:|:--------------------------------------------------------------
 202    | Seed the precache with data object; ETA returned, if possible
 401    | Authentication failure
 403    | Access denied to iRobot iRODS user
 404    | No such data object on iRODS
 405    | Method not allowed (only `GET`, `HEAD`, `POST`, `DELETE` and `OPTIONS` are supported)
 504    | Response timeout
 507    | Precache full

Note that if the data object's state is already in the precache, this
action will forcibly refetch it, providing the filesystem metadata has
changed.

#### `DELETE`

Delete a data object and its associated metadata from the precache. This
**does not** delete data from iRODS and is only for precache management;
it should be used sparingly -- in exceptional circumstances -- as the
precache is designed to manage itself automatically.

 Status | Semantics
:------:|:--------------------------------------------------------------
 204    | Data object removed from precache
 401    | Authentication failure
 409    | Inflight data object could not be deleted from the precache
 404    | No such data object in precache
 405    | Method not allowed (only `GET`, `HEAD`, `POST`, `DELETE` and `OPTIONS` are supported)
 504    | Response timeout

A data object can only be deleted from the precache if it is currently
not inflight. That is, it is not being fetched from iRODS or being
pushed by iRobot to a connected client.

### Administrative Endpoints

Administrative endpoints are exposed at the root and prefixed with an
underscore. They have a higher priority in the routing tree than the
data object endpoints, but should never mask data objects as they cannot
be contained within the iRODS "root collection". Only `GET` and `HEAD`
requests can be made to these endpoints, which can return the following:

 Status | Semantics
:------:|:--------------------------------------------------------------
 200    | Return the administrative data
 401    | Authentication failure
 405    | Method not allowed (only `GET`, `HEAD` and `OPTIONS` are supported)
 406    | Unsupported requested media type
 504    | Response timeout

Administrative endpoints will only ever return `application/json`. If
the `Accept` request header diverges from this, a `406 Not Acceptable`
response will be returned.

#### `_status`

iRobot's current state:

* `connections`
  * `active` The current number of active connections.
  * `total` The total number of requests made to iRobot.
* `precache`
  * `commitment` The size, in bytes, committed to the precache.
  * `checksum_rate`
    * `average` The average checksumming rate, in bytes/second,
      performed by iRobot.
    * `stderr` The standard error, in bytes/second, of the checksumming
      rate.
* `irods`
  * `active` The current number of active downloads from iRODS.
  * `download_rate` The rate, in bytes/second,
    * `average` The average download rate, in bytes/second, achieved by
      iRODS.
    * `stderr` The standard error, in bytes/second, of the download
      rate.

<!-- TODO: More?... -->

#### `_config`

iRobot's current configuration:

<!-- TODO -->

#### `_precache`

An overview of the contents of the precache. This will return an array
of objects of the following form:

* `path` Full path of the data object.

<!-- TODO: Other precache entity properties; MD5, status, ETA, etc. -->
