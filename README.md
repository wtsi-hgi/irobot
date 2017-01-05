# iRobot

iRODS-Keep brokerage service: Data from iRODS is requested for Arvados,
either directly by a job or from a trusted agent (e.g., [Cookie
Monster](https://github.com/wtsi-hgi/cookie-monster)), which is staged
on local disk and then pushed into Keep as a job's intermediary data.
The service also acts as a precache, to seed Arvados with data, as well
as managing a connection pool to iRODS.

## Installation

TODO

n.b., Uses Python 2.7 to maintain compatibility with the Arvados Python
SDK.

## Configuration

TODO

## API

TODO
