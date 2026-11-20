# Shopper behaviour

An online store's clickstream, grouped into sessions and classified into shopper types, both after the fact and while the session is still open.

## Shoppers and events

**Shopper**:
A person browsing the store, identified by the dataset's `user_id`.
_Avoid_: User, customer, visitor

**Event**:
One recorded shopper action at a point in time, of exactly one event type.
_Avoid_: Click, hit, message, row

**Event type**:
One of View, Cart add, Cart removal or Purchase.
_Avoid_: Action

**Event time**:
When the shopper performed the event, as recorded in the source data. Never the time the pipeline received it.
_Avoid_: Timestamp, arrival time

**Event ID**:
The stable identity of an event, derived from where it sits in the source files (the file's original name and the event's CSV record number after the header), so the same event always has the same ID however it enters the pipeline.

## Sessions

**Session**:
A shopper's run of events with no gap longer than the session gap. Sessions are always derived by this project, never taken from the source data.
_Avoid_: Visit, window, `user_session`

**Session gap**:
The longest silence (30 minutes) that can occur inside one session; a longer silence starts a new one.
_Avoid_: Timeout, inactivity window

**Source session**:
The session identifier supplied by the dataset (`user_session`). Used only to check how well our sessions agree with it.

**Open session**:
A session whose session gap has not yet elapsed, so more events may still join it.
_Avoid_: Live session, active session

**Closed session**:
A session whose session gap has elapsed; its events and shopper type are final.

## Classification

**Shopper type**:
The behavioural category assigned to one session. Exactly one of the six below; rules are checked in this order and the first match wins.
_Avoid_: Label, segment, persona, cluster

**Decisive buyer**:
A session that purchases after only a few views and never removes anything from the cart.

**Researcher**:
A session that purchases after many views and never removes anything from the cart.
_Avoid_: Considered buyer, slow buyer

**Hesitator**:
A session that removes something from the cart, or adds to the cart without purchasing.
_Avoid_: Cart abandoner

**Deal-hunter**:
A session whose viewed items are mostly priced below their category reference price.

**Browser**:
A session of several views with no cart activity.

**Bounce**:
A session of very few views and nothing else. Never contains a purchase or cart activity.
_Avoid_: Other

**Provisional shopper type**:
The shopper type of an open session given the events seen so far; it may change as events arrive.

**Final shopper type**:
The shopper type of a closed session.

**Dominant shopper type**:
The shopper type a shopper shows most often across their sessions, ignoring Bounce sessions; a tie goes to the type of their most recent session. A shopper with only Bounce sessions is a Bounce.
_Avoid_: User type, shopper profile

**Category reference price**:
The fixed median price of a product category (by `category_id`), computed once from the full history and used by both batch and streaming classification.
_Avoid_: Category median, average price

**Signal**:
A notice that an open session has met a signal trigger, so the store could act while the shopper is still present. At most one signal per session per trigger.
_Avoid_: Alert, notification

**Signal trigger**:
A condition on an open session that fires a signal the moment it becomes true and can never become untrue: a Cart removal, or an idle cart.

**Idle cart**:
An open session that added to the cart and has gone a set time without a Purchase.
_Avoid_: Abandoned cart (abandonment is only known once the session closes)

## Lateness

**Late event**:
An event that arrives after the pipeline has assumed all events up to its event time are in, but within the allowed lateness, so it still updates its session.
_Avoid_: Out-of-order event (out-of-order events are not necessarily late)

**Allowed lateness**:
How far behind (1 hour) an event may arrive and still count towards its session.

**Expired event**:
An event that arrives beyond the allowed lateness. It is kept aside and never changes a session.
_Avoid_: Late event, dropped event

**Rejected event**:
An event that fails the event schema and never reaches the store's event stream; it is kept in the dead-letter topic.
_Avoid_: Malformed event (that is the replayer's fault setting that produces them), bad message

## Ingestion

**Replay**:
Re-emitting historical events in event-time order at a chosen speed, as if they were happening now.
_Avoid_: Simulation, stream (as a noun for the process)

**Backfill**:
Loading historical events in bulk, without replaying them.
_Avoid_: Batch load, history load

**Ingest path**:
How an event entered the pipeline: by replay (`stream`) or by backfill (`backfill`).
