# The Precache

The precache mechanism is super-complicated, so how it's intended to
work is documented here.

<!-- TODO Write this out completely before implementing anything!! -->

## Calculating the ETA

We know the rates for downloading and checksumming, as well as the size
of the data we're processing and what's ahead of it in the queue. As
such, we can estimate processing times.

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
    STARTED  ┴

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
that entity is the current time, plus the duration for the next slot,
plus the average wait time for the data ahead of it, plus the time to
process itself:

    ETA = Now + W + Q + T
