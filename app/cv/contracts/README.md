# CVEvent handoff contract

`cv-event-v1` is the sole Computer Vision handoff envelope for:

- `ZONE_INTRUSION`
- `CROWD_THRESHOLD`
- `ABANDONED_OBJECT`

Lifecycle values are `START`, `UPDATE`, and `END`. The engine that owns a
lifecycle creates the `event_id` once (recommended format:
`{camera_id}_{event_short}_{counter:06d}`) and reuses it for every transition.
The contract stores wall-clock ISO-8601 time separately from non-negative
stream-relative seconds. Internal event timing may continue using a monotonic
clock, but a monotonic value must never be serialized as `event_time`.

## Confidence ownership

Builders require `cv_confidence` explicitly and never invent or combine scores.
Until each engine has a calibrated scalar, Phase 9 should use these deterministic
source rules and document any later calibration separately:

- intrusion: minimum detector confidence among persons included in the event;
- crowd: minimum detector confidence among confirmed persons counted;
- abandoned: current luggage-quality scalar when defined, otherwise minimum
  detector confidence across the luggage source tracks. Owner association stays
  separate in `evidence.owner_association_score` and is not multiplied in.

These rules preserve a conservative CV confidence without mapping it to severity.

## Phase 9 migration

Import builders from `app.cv.contracts`. Event engines should pass their computed
objects/evidence to a builder; an EventManager should own counters, lifecycle
deduplication, and stable IDs. Existing Phase 7C candidate semantics must be
reviewed before mapping a candidate to the locked `ABANDONED_OBJECT` taxonomy.
This package does not perform that promotion and does not implement Phase 9.
