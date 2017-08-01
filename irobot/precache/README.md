# The Precache

The precache mechanism is super-complicated, so how it's intended to
work is documented here.

## Anatomy of a Request

A request is made for a data object. While iRobot could be used for just
fetching metadata against a data object, its main purpose is to be a
data provider; as such, we schedule the fetching/production of
everything upon an initial request, regardless of the request type. In
subsequent requests for the same data object, we are more
discriminating.

* First we check if an entity for that data object exists within the
  precache. If it doesn't:

  * Check the data object exists in iRODS and that we have permission to
    access it. If not, raise an appropriate exception.

  * Fetch its metadata.

  * Check there is space within the defined limits of the precache to
    accommodate the entity's data, metadata and checksums. If not:

    * Attempt to clear invalidatable data from the precache to
      accommodate the request. If there's still not enough space, raise
      an exception.

  * Instantiate an entity on the basis of the metadata and the current
    time (for the last access time) and add it to the precache.

* Check we have, are planning to or are in the process of fetching data
  for the entity. If not:

  * Enqueue the asynchronous data fetching job.

  If/when data fetching is queued and a data request is made:

  * Raise an interrupt to alert the requestor that the fetching job has
    been submitted, with an estimated completion time (if possible).

  When data is available (or partially available) and a data request is
  made:

  * Update the entity's last access time.

  * Stream the data (or ranges, thereof) to the requestor. If checksums
    are available for the data (or ranges, thereof), include them in the
    output.

* When data fetching is complete, check we have, are planning to or are
  in the process of calculating its checksums. If not:

  * Enqueue the asynchronous checksumming job.

* When checksumming is complete, check our calculated checksum matches
  the iRODS checksum. If not:

  * Delete the fetched data and calculated checksum file.

  * Log a checksum mismatch failure.

  * Restart the data fetching (and, implicitly, checksumming) processes.

n.b., Metadata for data objects is relatively small and, while it is
persisted to disk, it remains part of the entity's in-memory state. When
it is not available, a blocking call -- rather than an asynchronous one
-- is used to fetch it from iRODS, as it won't block for long.

* Any metadata request will update the entity's last access time.

* A metadata request for a newly instantiated entity will return the
  metadata, rather than an estimated completion time for the data;
  however, the data fetching (and subsequent checksumming) will still be
  enqueued.

* A forced metadata request, when appropriate, will only refetch data
  (and checksumming) if the modification timestamp, size and/or checksum
  have changed from the original; otherwise, the metadata will be
  updated in-place.

## Cache Invalidation

The caching policy allows invalidation based either on time and/or
capacity. It should function similar to a stop-the-world garbage
collector, in terms of locking, for simplicity's sake.

New entities can only be put in the precache if they are known to fit.
Only entities that are not currently being processed (i.e., not fetching
or checksumming data) may be invalidated.

### Temporal Invalidation

This is only relevant if temporal invalidation is enabled:

* A process should be scheduled to run periodically; say, with a period
  of half the expiration limit.

* When run, any entities that exceed the expiration limit are
  invalidated and freed.

* If a request for an invalid entity is made before it is culled, then
  that should trigger the cull and thus restart data fetching and
  checksumming. The justification being that, while the data *is* in the
  precache, it has expired per the configured policy.

### Capacity Invalidation

This is only relevant if the precache size is limited:

* When a new request is received that overflows the precache, entities
  may be invalidated and freed based on:

  * Any temporal invalidation (where appropriate) that has yet to be
    freed in the scheduled cull.

  * Their age, where the oldest entities (beyond some defined threshold)
    will be culled first. In this instance, data should only be deleted
    if enough space can be freed to accomodate the new request;
    otherwise, the invalidation is cancelled.

### Manual Invalidation

A `POST` request is effectively manual invalidation. It will delete any
state already existing in the precache, presuming its metadata indicate
that it's changed, regardless of any current users. It is assumed that
manual invalidation will be an exceptional case, hence not protecting
against this kind of DoS attack.

## Miscellany

* Upon instantiation, the precache must load its in-memory state from
  the tracking database. All state changes during runtime must be
  persisted back to the tracking database.

* Upon instantiation, the precache must handle any currently existing
  entities from a previous run that is in a queued or in progress state.
  These entities must be cancelled and requeued; any partial data that
  has already been fetched should be deleted.

* Processing rates are calculated by the tracking database, but only
  cover the current items being tracked. As such, the precache must
  maintain a "last known" rate in-memory, in the case when the precache
  is emptied.

## Calculating the ETA

We know the rates for fetching (and checksumming), as well as the size
of the data we're processing and what's ahead of it in the queue. As
such, we can estimate processing times.

(Note that, while we have enough data to do so, we don't need to
calculate checksum ETAs as they're not used downstream.)

If an estimate is required for an entity that is currently being
processed or about to enter the queue (i.e., that overlaps the available
number of workers), then we use the processing start time, plus the
entity size divided by the processing rate, as our ETA:

    ETA = Start + (Size / Rate)

Otherwise:

            QUEUED
            QUEUED   ← Estimate required
            QUEUED   ⎫
            …        ⎬ Ahead in the queue
            QUEUED   ⎭
            QUEUED   ⎫
            STARTED  ⎪
            STARTED  ⎬ Worker pool
            …        ⎪
    Head →  STARTED  ⎭

Consider the entities in the queue that have started to be processed, or
are about to be. The wait time for the next available slot will be the
shortest time based on these entities' sizes, start times and processing
rates from the current time. Call this duration *W*.

Now consider the entities in the queue that are ahead of the entity for
which we want an estimate, but have yet to be picked up by the worker
pool: Take the sum of their sizes, divided by the number of workers, and
calculate the processing time based on the rate. Call this duration *Q*.

The processing time for the requested entity, *T*, is easily calculated
as that entity's size divided by the processing rate. Thus the ETA for
that entity is the base time, plus the duration for the next slot, plus
the average wait time for the data ahead of it, plus the time to process
itself:

    ETA = Base + W + Q + T

Where the base time for fetching data is the current time. (The base
time for checksumming would be the fetching ETA.)

Note that this estimate is not necessarily accurate, insofar as the
concurrency makes accuracy intractable. This is seen as a reasonable
compromise.
