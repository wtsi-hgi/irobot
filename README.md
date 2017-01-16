# iRobot

iRODS-Keep brokerage service: Data from iRODS is requested for Arvados,
either directly by a job or from a trusted agent (e.g., [Cookie
Monster](https://github.com/wtsi-hgi/cookie-monster)), which is staged
on local disk and then pushed into Keep as a job's intermediary data.
The service also acts as a precache, to seed Arvados with data, as well
as managing a connection pool to iRODS.

## Installation

iRobot is fully containerised, using Docker. The container can be built
using the `build.sh` script:

    build.sh AUTH_METHOD [USER] 

Build script requirements:

* Bash 4 (or newer)
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
then builds the container named `hgi/irobot`, with the `USER` given as
its tag.

To launch the container:

    docker run -v /path/to/your/precache/directory:/precache \
               -v /etc/krb5.conf:/etc/krb5.conf \
               -v /path/to/your/irobot.conf:/home/USER/irobot.conf \
               -p TODO:TODO \
               hgi/irobot:USER

(Note that bind mounting `/etc/krb5.conf` is only necessary when using
Kerberos authentication.)

## Configuration

TODO

## API

TODO
