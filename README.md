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
- [x] HTTP interface
  - [x] Request logging middleware
  - [x] Error catching middleware
  - [x] Response timeout middleware
  - [x] Authentication middleware
  - [x] Data object endpoint
    - [x] `GET` and `HEAD`
      - [x] Data request
      - [x] Ranged data request
        - [x] Range parser
      - [x] Metadata request
    - [x] `POST`
    - [x] `DELETE`
  - [x] Administrative endpoints
    - [x] Common middleware
    - [x] Status endpoint
    - [x] Configuration endpoint
    - [x] Precache manifest endpoint
- [x] Installation/containerisation
  - [x] Base system
  - [x] Kerberos support
  - [x] iRobot (n.b., change to master branch for release)
- [ ] Testing
  - [ ] Unit testing
  - [ ] Integration testing
  - [ ] User acceptance testing
- [x] Documentation

## Installation

iRobot is fully containerised, using Docker. The container image can be
built using:
```bash
docker build -f Dockerfile -t mercury/irobot .
```

To launch the container:
```bash
docker run -v /path/to/your/precache/directory:/precache \
           -v /path/to/your/irods_environment.json:/root/.irods/irods_environment.json \
           -v /path/to/your/irobot.conf:/root/irobot.conf \
           -p 5000:5000 \
           mercury/irobot
```
An example configuration can be found in `irobot.conf.sample`.

For use with native iRODS authentication, either bind mount the `.irodsA` file onto `/root/.irods/.irodsA` (e.g. 
`-v /path/to/your/.irodsA:/root/.irods/.irodsA:ro`) or pass it in via the `IRODS_PASSWORD` environment variable (e.g.
`-e IRODS_PASSWORD=xxx`).

For use with Kerberos authentication, bind mount the `krb5.conf` file onto `/etc/krb5.conf` 
(e.g. `-v /path/to/your/krb5.conf:/etc/krb5.conf`).


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

* **`realm`** Optional free text input for the basic authentication
  realm parameter.

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

* `Bearer <payload>`, where the payload is an API token supplied by
  Arvados for Arvados authentication. (Note that the challenge for
  Arvados authentication will include the API host as its `realm`.)

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
 206    | Return ranges of data object
 304    | Data object matches that expected by client
 401    | Authentication failure
 403    | Access denied to iRobot iRODS user
 404    | No such data object on iRODS
 405    | Method not allowed (only `GET`, `HEAD`, `POST`, `DELETE` and `OPTIONS` are supported)
 406    | Unsupported requested media type
 416    | Invalid range request
 502    | An invalid operation occurred while interacting with iRODS
 504    | Response timeout
 507    | Precache full

A `HEAD` request can be made to the data object endpoint to facilitate
discovery and status tracking, without the overhead of a full `GET`.
That is, the same actions described below will be invoked on a `HEAD`
request, but only the response headers will be returned.

##### Using the `Accept` Request Header

The `Accept` request header is used productively to fetch an appropriate
representation of the specific data object, per the semantics of [HTTP
content negotation](https://tools.ietf.org/html/rfc7231#section-5.3.2):

* If it is omitted, or `application/octet-stream` is the primarily
  accepted media type, then the data (or ranges, thereof) for the
  specified data object will be returned, with checksums if available.

* If the primarily accepted media type is
  `application/vnd.irobot.metadata+json`, then a JSON representation of
  the metadata (see below) for the specified data object will be
  returned.

* Otherwise, a `406 Not Acceptable` response will be returned.

Note that, arguably, serving very different representations from the
same endpoint breaks the true purpose of content negotiation. However
the protocol followed by iRobot is seen as a better trade-off, given
its primary objective of fetching data. If, however, this representation
duplicity is too much for you to stomach, you can simply stick a reverse
proxy in front of iRobot with an appropriate set of rewrite rules.

##### Client Cache Validity

The response will always include the `ETag` header with its value
corresponding to the MD5 checksum of the data object cached by iRobot,
as calculated by iRODS. (iRobot will also calculate its own MD5 sum, to
check they match.) This will allow the client to verify it is requesting
the same version of the data object that it is expecting.

A client can ensure this programmatically by using the `If-None-Match`
request header, with the given entity tag. If the tags match, a `304 Not
Modified` response will be returned; otherwise, a full response will be
returned.

This behaviour will also be true of a range request, so if a client
wishes to fetch a range it doesn't have from a source it's seen before,
then it would either make two requests -- first with the `If-None-Match`
header then the second without -- or a single request without the
`If-None-Match` header, that would need to be analysed by the client.

##### Fetching Data

Fetching of the data supports range requests using the `Range` request
header. If this header is present and the data exists in its entirety,
it will be returned with a `206 Partial Content` response under the
`multipart/byteranges` media type, where byte ranges in the response
will have the media type `application/octet-stream` and include an
entity tag of the range MD5 checksum, if one exists. The ranges may
therefore be chunked differently than requested, so that they align with
the precache checksum chunk size, but the requested range will be fully
satisfied.

If the `Range` request header is omitted, then the entirety of the data
will be returned as a `200 OK` response, with media type
`application/octet-stream`. If a range request is not satisfiable due to
the request being out-of-bounds, then a `416 Range Not Satisfiable`
response will be issued.

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

    iRobot-ETA: 2017-09-25T12:34:56Z+0000 +/- 123

A client may choose to use this information to inform the rate at which
it reissues requests.

##### Metadata Response

When fetching data object metadata, the response will be of media type
`application/vnd.irobot.metadata+json`: A JSON object with the following
keys:

* `checksum` The MD5 checksum calculated by iRODS
* `size` The file size in bytes
* `created` The creation timestamp (Unix epoch)
* `modified` The modification timestamp (Unix epoch)
* `avus` A list of iRODS AVU metadata

AVUs are JSON objects with the following keys:

* `attribute` The metadata attribute
* `value` The metadata value
* `units` The metadata unit (optional)

#### `POST`

Seed the precache with the data object, its metadata and calculate
checksums; thus warranting its title of "precache"!

 Status | Semantics
:------:|:--------------------------------------------------------------
 201    | Seeded the precache with data object
 202    | Seed the precache with data object; ETA returned, if possible
 401    | Authentication failure
 403    | Access denied to iRobot iRODS user
 404    | No such data object on iRODS
 405    | Method not allowed (only `GET`, `HEAD`, `POST`, `DELETE` and `OPTIONS` are supported)
 409    | Inflight or contended data object could not be refetched
 502    | An invalid operation occurred while interacting with iRODS
 504    | Response timeout
 507    | Precache full

Note that if the data object's state is already in the precache, this
action will forcibly refetch it, providing the filesystem metadata has
changed (file size, checksum and timestamps) and the precached data
object is not currently inflight or contended. That is, it is not being
fetched from iRODS or being pushed by iRobot to a connected client.

#### `DELETE`

Delete a data object and its associated metadata from the precache. This
**does not** delete data from iRODS and is only for precache management;
it should be used sparingly -- in exceptional circumstances -- as the
precache is designed to manage itself automatically.

 Status | Semantics
:------:|:--------------------------------------------------------------
 204    | Data object removed from precache
 401    | Authentication failure
 404    | No such data object in precache
 405    | Method not allowed (only `GET`, `HEAD`, `POST`, `DELETE` and `OPTIONS` are supported)
 409    | Inflight or contended data object could not be deleted from the precache
 504    | Response timeout

A data object can only be deleted from the precache if it is currently
not inflight or contended.

### Administrative Endpoints

Administrative endpoints are exposed at the root; they have a higher
priority in the routing tree than the data object endpoints, but should
never mask data objects as they cannot be contained within the iRODS
"root collection". Only `GET` and `HEAD` requests can be made to these
endpoints, which can return the following:

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

#### `/status`

iRobot's current state:

* `authenticated_user` The authenticated user of the current request.
* `connections`
  * `active` The current number of active connections.
  * `total` The total number of requests made to iRobot.
  * `since` The Unix time when iRobot was started.
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

#### `/config`

iRobot's current configuration, as a JSON object.

#### `/manifest`

An overview of the contents of the precache. This will return a JSON
array of objects of the following form:

* `path` Full iRODS path of the data object.
* `availability` A JSON object where each key's value is a string of
  `Pending`, an ETA (in the same format as the ETA response), or
  `Ready` for the following keys:
  * `data`
  * `metadata`
  * `checksums`
* `last_accessed` The last access timestamp.
* `contention` The number of currently active requests.

### Error Responses

All `400` and `500`-series errors (i.e., client and server errors,
respectively) will be returned as `application/json`. The response body
will be a JSON object with three elements: `status`, containing the HTTP
status code; `reason`, containing the HTTP status reason; and
`description` containing a human-readable description of the problem.
