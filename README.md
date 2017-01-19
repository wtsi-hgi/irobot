# iRobot

<!-- TODO Change to master branch on release -->
[![Build Status](https://travis-ci.org/wtsi-hgi/irobot.svg?branch=develop)](https://travis-ci.org/wtsi-hgi/irobot)
[![Test Coverage](https://codecov.io/gh/wtsi-hgi/irobot/branch/develop/graph/badge.svg)](https://codecov.io/gh/wtsi-hgi/irobot)

iRODS-Keep brokerage service: Data from iRODS is requested for Arvados,
either directly by a job or from a trusted agent (e.g., [Cookie
Monster](https://github.com/wtsi-hgi/cookie-monster)), which is staged
on local disk and then pushed into Keep as a job's intermediary data.
The service also acts as a precache, to seed Arvados with data, as well
as managing a connection pool to iRODS.

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
               -p TODO:TODO \
               hgi/irobot:USER

(Note that bind mounting `/etc/krb5.conf` is only necessary when using
Kerberos authentication. A `cron` job runs in the Kerberos container to
renew credentials with the KDC periodically; if the container is down
for any significant amount of time, this may fail and you'll have to
rebuild the image.)

## Configuration

The `irobot.conf` configuration is not copied into the image and ought
to be bind mounted at runtime. This allows you to make configuration
changes without rebuilding. An example configuration can be found in
`irobot.conf.sample`.

### Precache Policy

* **`size`** The maximum size of the precache. It can be set to
  `unlimited`, where it is allowed to grow indefinitely (until the disk
  fills), or to a defined limit. Upon reaching the limit, the oldest
  files (in terms of access time) are removed.

  The limit should be the number of bytes, optionally suffixed with `B`.
  Decimal (base 1000: `k`, `M`, `G`, `T`) or binary (base 1024: `ki`,
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

TODO: Other stuff...

## API

TODO
