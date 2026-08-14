---
phase: 2
title: "Unify engines and lifecycle"
status: completed
priority: P1
effort: 2.5d
dependencies: [1]
---

# Phase 2: Unify engines and lifecycle

## Overview

Adapt existing intrusion, crowd, and Phase7C reasoning to lifecycle signals, then centralize stable IDs/dedup in one manager. Reuse, do not copy Phase7C core.

Progress: complete. Three adapters and one lifecycle manager validated by the 78-test + 8-subtest CV suite and 4/4 real-video regression.

## Implementation Tracking

- [x] Three lifecycle adapters and internal signal contract implemented.
- [x] Per-worker event manager with stable lifecycle IDs/dedup implemented.
- [x] Manager/adapter regression included in final 78 + 8 passing result.
- [x] Broader required CV regression and real-media production-path validation complete.

## Requirements and Data Flow

- Shared TrackStore snapshot → engines. Intrusion reads persons; crowd counts distinct persons; Phase7C reads person/luggage history.
- Engine signal → manager key `(camera,event_type,entity/zone)` → stable active ID → START once, bounded UPDATE, END once → CVEvent v1.
- Preserve current rule state machines at `app/events/intrusion.py:32-115`, `app/events/crowd.py:20-60`; replace their one-shot candidate output through thin adapters.
- Production adapter imports Phase7C core normally; remove `sys.path` mutation currently at `app/cv/phase8_event_adapter.py:104-107`.

## Related Code Files / Exclusive Ownership

- Create: `app/cv/events/intrusion-adapter.py`, `crowd-adapter.py`, `phase7c-abandoned-adapter.py`, `event-signal.py`; `app/cv/event-manager.py`.
- Modify: `kaggle_pipeline/phase7c_kernel/phase7c_core.py` only if a narrow incremental API seam is required; behavior unchanged.
- Create tests: `tests/unit/test_cv_event_manager.py`, `test_phase7c_production_adapter.py`, `test_intrusion_lifecycle_adapter.py`, `test_crowd_lifecycle_adapter.py`.

## Implementation Steps

1. Define internal signal contract with event key/state/time/objects/evidence; not public/backend API.
2. Wrap current intrusion/crowd state transitions; add END and UPDATE without per-frame event spam.
3. Add thin streaming Phase7C adapter retaining rolling quality, stitching, stationary ~3s, owner association/history, owner-away ~5s, media seconds.
4. Manager owns per-worker active registry, monotonic camera-local counters, cooldown and dedup. Verify lifetime: instantiated per `CVWorker`, never process-global.
5. Convert managed lifecycle to existing builders and validate before output.

## Test Matrix / Success Criteria

| Level | Scenarios |
|---|---|
| Unit | START→UPDATE→END same ID; duplicate signal suppressed; re-entry gets new ID; time reversal rejected; empty tracks close active event |
| Unit | intrusion exit/re-entry; crowd threshold/hold/release; Phase7C owner return, false person, fragmented luggage stitch |
| Contract | exact objects/evidence for all states/types; optional quality emitted only when scalar exists |

- [x] Three event types only; stable IDs; no per-frame spam.
- [x] Manager instance isolation proven across two cameras/workers.

## Risks / Rollback / Security

- High × High: duplicate lifecycle ownership between engine dedupe and manager. Mitigation: adapters emit facts/transitions; manager sole output dedupe authority; transition matrix tests.
- High × High: batch Phase7C API forces full-history recomputation. Mitigation: thin stateful adapter or minimal incremental seam; benchmark bounded per-frame growth.
- Medium × High: track expiry absent from TrackStore (`app/cv/track_store.py:63-64`). Mitigation: define active snapshot/expiry before END semantics; test lost-buffer boundary.
- Rollback: new modules/tests are unreachable until Phase 3 switch.

## Next Steps

Phase 3 production wiring completed.
