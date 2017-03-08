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
  id          integer  primary key,
  irods_path  text     not null unique
);

create index if not exists do_id on data_objects(id);
create index if not exists do_irods_path on data_objects(irods_path);

create table if not exists do_modes (
  id             integer  primary key,
  data_object    integer  references data_objects(id) on delete cascade,
  mode           MODE     references modes(id),
  precache_path  text     not null unique,

  unique (data_object, mode)
);

create index if not exists dom_id on do_modes(id);
create index if not exists dom_file on do_modes(data_object, mode);

-- This is for convenience, to enter new master data objects
create view if not exists do_requests as
  select data_objects.id,
         data_objects.irods_path,
         do_modes.precache_path
  from   data_objects
  join   do_modes
  on     do_modes.data_object = data_objects.id
  where  do_modes.mode        = 1;

create trigger if not exists auto_request
  instead of insert on do_requests for each row
  begin
    insert into data_objects(irods_path) values (NEW.irods_path);
    insert into do_modes(data_object, mode, precache_path) values (last_insert_rowid(), 1, NEW.precache_path);
  end;

-- Last access for master data objects only
create table if not exists last_access (
  id           integer    primary key,
  data_object  integer    references data_objects(id) on delete cascade,
  last_access  TIMESTAMP  not null default (strftime('%s', 'now'))
);

create index if not exists la_id on last_access(id);
create index if not exists la_data_object on last_access(data_object);
create index if not exists la_last_access on last_access(last_access);

create trigger if not exists auto_first_access
  after insert on do_modes for each row when NEW.mode = 1
  begin
    insert into last_access(data_object) values (NEW.id);
  end;

create table if not exists data_sizes (
  id        integer   primary key,
  dom_file  integer   references do_modes(id) on delete cascade,
  datatype  DATATYPE  references datatypes(id),
  size      integer   not null check (size > 0),

  unique (dom_file, datatype)
);

create index if not exists ds_id on data_sizes(id);
create index if not exists ds_file on data_sizes(dom_file, datatype);

create view if not exists precache_commitment as
  select sum(size) as size
  from   data_sizes;

create table if not exists status_log (
  id         integer    primary key,
  timestamp  TIMESTAMP  not null default (strftime('%s', 'now')),
  dom_file   integer    references do_modes(id) on delete cascade,
  datatype   DATATYPE   references datatypes(id),
  status     STATUS     references statuses(id),

  unique (dom_file, datatype, status)
);

create index if not exists log_id on status_log(id);
create index if not exists log_timestamp on status_log(timestamp);
create index if not exists log_file on status_log(dom_file, datatype);
create index if not exists log_datatype on status_log(datatype);
create index if not exists log_status on status_log(status);
create index if not exists log_file_status on status_log(dom_file, datatype, status);

create trigger if not exists auto_first_status
  after insert on do_modes for each row
  begin
    insert into status_log(dom_file, datatype, status)
      select NEW.id, id, 1 from datatypes;
  end;

create view if not exists current_status as
  select    do_modes.data_object,
            do_modes.mode,
            newest.datatype,
            newest.timestamp,
            newest.status
  from      do_modes
  join      status_log as newest
  on        newest.dom_file = do_modes.id
  left join status_log as newer
  on        newer.dom_file  = newest.dom_file
  and       newer.datatype  = newest.datatype
  and       newer.timestamp > newest.timestamp
  where     newer.id is null;

-- NOTE This relies on a user-defined "stderr" aggregate function that
-- must be implemented in the host environment
create view if not exists production_rates as
  with _log as (
    select dom_file,
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
    on     finished.dom_file   = started.dom_file
    and    finished.datatype   = started.datatype
    join   data_sizes
    on     data_sizes.dom_file = started.dom_file
    and    data_sizes.datatype = 1
    where  started.status      = 2
    and    finished.status     = 3
  )
  select   case when datatype = 1 then "download" else "checksum" end as process,
           avg(1.0 * size / duration) as rate,
           stderr(1.0 * size / duration) as stderr
  from     _processing
  group by datatype;

commit;

reindex;
vacuum;
