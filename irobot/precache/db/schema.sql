/*
Copyright (c) 2017 Genome Research Ltd.

Author: Christopher Harrison <ch12@sanger.ac.uk>

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your
option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
Public License for more details.

You should have received a copy of the GNU General Public License along
with this program. If not, see <http://www.gnu.org/licenses/>.
*/

pragma foreign_keys = ON;
pragma locking_mode = EXCLUSIVE;

begin exclusive transaction;

create table if not exists datatypes (
  id           integer  primary key,
  description  text     not null unique
) without rowid;

insert or ignore into datatypes(id, description) values (1, "data"),
                                                        (2, "metadata"),
                                                        (3, "checksums");

create table if not exists statuses (
  id           integer  primary key,
  description  text     not null unique
) without rowid;

-- NOTE "unknown" and "failed" aren't used by the tracking DB, they just
-- exist to reflect the internal application enumeration type
insert or ignore into statuses(id, description) values (1, "queued"),
                                                       (2, "started"),
                                                       (3, "finished"),
                                                       (4, "unknown"),
                                                       (5, "failed");

create table if not exists data_objects (
  id             integer    primary key,
  irods_path     text       not null unique,
  precache_path  text       not null unique,
  last_access    TIMESTAMP  not null default (strftime('%s', 'now'))
);

create index if not exists do_id on data_objects(id);
create index if not exists do_irods_path on data_objects(irods_path);
create index if not exists do_last_access on data_objects(last_access);

create table if not exists data_sizes (
  id           integer   primary key,
  data_object  integer   references data_objects(id) on delete cascade,
  datatype     DATATYPE  references datatypes(id),
  size         integer   not null check (size >= 0),

  unique (data_object, datatype)
);

create index if not exists ds_id on data_sizes(id);
create index if not exists ds_file on data_sizes(data_object, datatype);

create view if not exists precache_commitment as
  with _sizes as (
    select size
    from   data_sizes
    union
    select 0 as size
  )
  select sum(size) as size
  from   _sizes;

create table if not exists status_log (
  id           integer    primary key,
  timestamp    TIMESTAMP  not null default (strftime('%s', 'now')),
  data_object  integer    references data_objects(id) on delete cascade,
  datatype     DATATYPE   references datatypes(id),
  status       STATUS     references statuses(id),

  unique (data_object, datatype, status)
);

create index if not exists log_id on status_log(id);
create index if not exists log_timestamp on status_log(timestamp);
create index if not exists log_file on status_log(data_object, datatype);
create index if not exists log_datatype on status_log(datatype);
create index if not exists log_status on status_log(status);
create index if not exists log_file_status on status_log(data_object, datatype, status);

create trigger if not exists auto_first_status
  after insert on data_objects for each row
  begin
    insert into status_log(data_object, datatype, status)
      select NEW.id, id, 1 from datatypes;
  end;

-- Status is strictly increasing and unique for each data object file.
-- As such, we use that (instead of timestamp with only one second
-- resolution) to order the status log
create view if not exists current_status as
  select    data_objects.id as data_object,
            newest.datatype,
            newest.timestamp,
            newest.status
  from      data_objects
  join      status_log as newest
  on        newest.data_object = data_objects.id
  left join status_log as newer
  on        newer.data_object  = newest.data_object
  and       newer.datatype     = newest.datatype
  and       newer.status       > newest.status
  where     newer.id          is null;

-- NOTE This relies on a user-defined "stderr" aggregate function that
-- must be implemented in the host environment
create view if not exists production_rates as
  with _log as (
    select data_object,
           datatype,
           timestamp,
           status
    from   status_log
    where  datatype in (1, 3)
    and    status   in (2, 3)
  ),
  _processing as (
    select started.datatype, 
           data_sizes.size,
           finished.timestamp - started.timestamp as duration
    from   _log as started
    join   _log as finished
    on     finished.data_object   = started.data_object
    and    finished.datatype      = started.datatype
    join   data_sizes
    on     data_sizes.data_object = started.data_object
    and    data_sizes.datatype    = 1
    where  started.status         = 2
    and    finished.status        = 3
  )
  select   datatype as process,
           avg(1.0 * size / duration) as rate,
           stderr(1.0 * size / duration) as stderr
  from     _processing
  group by datatype;

-- Reset files in a bad state (i.e., "producing")
with _bad_records as (
  select status_log.id
  from   current_status
  join   status_log
  on     status_log.data_object = current_status.data_object
  and    status_log.datatype    = current_status.datatype
  and    status_log.status      = current_status.status
  where  current_status.status = 2
)
delete
from   status_log
where  id in (select id from _bad_records);

commit;

reindex;
vacuum;
