# The Precache

The precache mechanism is super-complicated, so how it's intended to
work is documented here.

## Anatomy of a Request

A request is made for a data object. While iRobot could be used for just
fetching metadata against a data object, its main purpose is to be a
data provider; as such, we get everything on an initial request,
regardless of its type. In subsequent requests for the same data object,
we are more discriminating.

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

  * Instantiate a master entity on the basis of the metadata and the
    current time (for the last access time) and add it to the precache.

  ...If it does exist and a force (data) request is made when no
  switchover state is present:

  * Check we still have access to the data object in iRODS. If not,
    raise an appropriate exception.

  * Fetch its metadata and check it against the master metadata. If the
    modification date and/or checksum haven't changed, then raise a
    cancellation interrupt.

  * Check there is space to accommodate the switchover data, metadata
    and checksums. If not:

    * Attempt to clear invalidatable data from the precache to
      accommodate the request. If there's still not enough space, raise
      an exception.

  * Set the switchover state of the entity on the basis of the metadata
    and update the last access time.

* Check we have, are planning to or are in the process of fetching data
  (or switchover data, for a force request) for the entity. If not:

  * Enqueue the asynchronous data fetching job.

  If/when data fetching is queued or in progress and a data or checksum
  request is made:

  * Raise an interrupt to alert the requestor that the fetching job has
    been submitted, with an estimated completion time (if possible).

  When data is available and a data request is made:

  * Update the entity's last access time.

  * Stream the data (or ranges, thereof) to the requestor.

* When data fetching is complete, check we have, are planning to or are
  in the process of calculating its checksums. If not:

  * Enqueue the asynchronous checksumming job.

  If/when checksumming is queued or in progress and a checksum request
  is made:

  * Raise an interrupt to alert the requestor that the checksumming job
    has been submitted, with an estimated completion time (if possible).

  When checksums are available and a checksum request is made:

  * Update the entity's last access time.

  * Return the checksums (or ranges, thereof) to the requestor.

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
  (and checksumming) if the modification timestamp and/or checksum have
  changed from the original; otherwise, the master metadata will be
  updated in-place.

## Cache Invalidation

The caching policy allows invalidation based either on time and/or
capacity. It should function similar to a stop-the-world garbage
collector, in terms of locking, for simplicity's sake.

New entities can only be put in the precache if they are known to fit.
Only entities that are not currently being processed (i.e., not fetching
or checksumming data for either their master or switchover states) may
be invalidated.

### Temporal Invalidation

This is only relevant if temporal invalidation is enabled:

* A process should be scheduled to run periodically; say, with a period
  of half the expiration limit.

* When run, any entities that exceed the expiration limit are
  invalidated and freed.

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

## Miscellany

* Upon instantiation, the precache must load its in-memory state from
  the tracking database. All state changes during runtime must be
  persisted back to the tracking database.

* Upon instantiation, the precache must handle any currently existing
  entities from a previous run that is in a queued or in progress state.
  These entities must be cancelled and requeued; any partial data that
  has already been fetched should be deleted.

## Calculating the ETA

We know the rates for fetching and checksumming, as well as the size of
the data we're processing and what's ahead of it in the queue. As such,
we can estimate processing times.

If an estimate is required for an entity that is currently being
processed or about to enter the queue (i.e., that overlaps the available
number of workers), then we use the processing start time, plus the
entity size divided by the processing rate, as our ETA.

Otherwise:

            QUEUED
            QUEUED   * Estimate required
            QUEUED   ┬
            ...      │ Ahead in the queue
            QUEUED   ┴
            QUEUED   ┬
            STARTED  │
            STARTED  │ Worker pool
            ...      │
    Head →  STARTED  ┴

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

* The base time for fetching data is the current time.

* The base time for checksumming time is the fetching ETA.

Note that this estimate is not necessarily accurate, insofar as the
concurrency makes accuracy intractable. This is seen as a reasonable
compromise.
