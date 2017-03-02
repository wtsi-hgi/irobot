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

create table if not exists datatypes (
  id           integer  primary key,
  description  text     not null unique
) without rowid;

insert or ignore into datatypes(id, description) values (1, "data"),
                                                        (2, "metadata"),
                                                        (3, "checksums");

create table if not exists modes (
  id           integer  primary key,
  description  text     not null unique
) without rowid;

insert or ignore into modes(id, description) values (1, "master"),
                                                    (2, "switchover");

create table if not exists statuses (
  id           integer  primary key,
  description  text     not null unique
) without rowid;

insert or ignore into statuses(id, description) values (1, "requested"),
                                                       (2, "producing"),
                                                       (3, "ready");

create table if not exists data_objects (
  id             integer  primary key,
  mode           integer  references modes(id),
  irods_path     text     not null,
  precache_path  text     not null,

  unique (mode, irods_path, precache_path)
);

create index if not exists do_id on data_objects(id);
create index if not exists do_file on data_objects(mode, irods_path, precache_path);
create index if not exists do_irods_path on data_objects(irods_path);
create index if not exists do_precache_path on data_objects(precache_path);

create table if not exists data_sizes (
  id           integer  primary key,
  data_object  integer  references data_objects(id) on delete cascade,
  datatype     integer  references datatypes(id),
  size         integer  not null check (size > 0),

  unique (data_object, datatype)
);

create index if not exists ds_id on data_sizes(id);
create index if not exists ds_file on data_sizes(data_object, datatype);

create view if not exists current_usage as
  select sum(size)
  from   data_sizes;

create table if not exists status_log (
  id           integer    primary key,
  timestamp    TIMESTAMP  not null default (strftime('%s', 'now')),
  data_object  integer    references data_objects(id) on delete cascade,
  datatype     integer    references datatypes(id),
  status       integer    references statuses(id),

  unique (data_object, datatype, status)
);

create index if not exists log_id on status_log(id);
create index if not exists log_timestamp on status_log(timestamp);
create index if not exists log_file on status_log(data_object, datatype);
create index if not exists log_datatype on status_log(datatype);
create index if not exists log_status on status_log(status);
create index if not exists log_file_status on status_log(data_object, datatype, status);

create view if not exists current_status as
  select    data_objects.id,
            data_objects.mode,
            data_objects.irods_path,
            newest.datatype,
            newest.timestamp,
            newest.status
  from      data_objects
  join      status_log as newest
  on        newest.data_object = data_objects.id
  left join status_log as newer
  on        newer.data_object = newest.data_object
  and       newer.datatype    = newest.datatype
  and       newer.timestamp   > newest.timestamp
  where     newer.id is null;

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
  select   case when datatype = 1 then "download" else "checksum" end as process,
           avg(1.0 * size / duration) as rate,
           stderr(1.0 * size / duration) as stderr
  from     _processing
  group by datatype;

create trigger if not exists auto_request
  after insert on data_objects for each row
  begin
    insert into status_log(data_object, datatype, status) values (NEW.id, 1, 1);
    insert into status_log(data_object, datatype, status) values (NEW.id, 2, 1);
    insert into status_log(data_object, datatype, status) values (NEW.id, 3, 1);
  end;

reindex;
vacuum;
