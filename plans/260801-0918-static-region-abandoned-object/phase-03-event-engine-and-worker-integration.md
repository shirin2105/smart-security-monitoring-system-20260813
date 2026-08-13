---
phase: 3
title: "Event engine and worker integration"
status: completed
priority: P1
effort: 4h
dependencies: [1, 2]
---

# Phase 03: Event engine and worker integration

## Context Links

- `app/events/abandoned_object.py:155-254` owns current class-dependent state/event creation.
- `app/cv/worker.py:44-70,84-100` constructs detector/engines and routes frames.
- `configs/models.yaml:1-6` currently requests person plus luggage classes.
- `tests/unit/test_abandoned_object.py:8-61` protects the former state flow.

## Overview

Replace luggage-track candidate generation with static-region observations while keeping person detection, engine signature, candidate schema, evidence, dedupe, and other event engines compatible.

## Requirements

- Functional: worker runs YOLO for persons, static detector on raw frame, supplies matured regions to abandoned engine, applies nearest-person/proximity context, emits one event per region, and clears/re-arms after removal.
- Non-functional: `evaluate(tracks, frame_data)` remains callable; feature switch permits rollback to tracked-class source during migration.

## Architecture and data flow

Worker branches each sampled frame: `(A) YOLO person -> tracker/store -> all engines`, `(B) raw frame -> static detector -> abandoned engine region inbox`. Engine correlates region center with current person foot points, times absence via deterministic timestamps, captures evidence, dedupes stable region ID, then emits existing `EventCandidate`. Avoid adding shared region state to `TrackStore`: it is worker/camera scoped (`app/cv/worker.py:18-52`).

## Related Code Files / Ownership

- Modify: `app/events/abandoned_object.py`, `app/cv/worker.py`, `configs/models.yaml`, `tests/unit/test_abandoned_object.py`, `tests/integration/test_phase4_integration.py`
- Create: `tests/integration/test_static_abandoned_pipeline.py`
- Delete: none

## Implementation Steps

1. Add tests for region-with-near-person -> person leaves -> event; no-person policy; person remains; region clears; duplicate suppression.
2. Refactor engine internals around stable region IDs. Preserve constructor/evaluate and expose a narrow region submission method or optional injected detector—choose one, not both.
3. Instantiate exactly one static detector per worker/camera. Route raw frame before event evaluation; keep person tracks for intrusion/crowd.
4. Change YOLO default target classes to `[0]` only after integration tests pass; read `allowed_classes` only in compatibility mode.
5. Preserve output fields; use region ID in `trackIds` only if integer-stable, otherwise keep `trackIds=[]` and encode region identity solely in candidate/dedupe IDs. Do not alter schema to force legacy semantics.

## Todo List

- [x] Replace old unit fixture with static-observation cases while retaining one compatibility test.
- [x] Integrate detector into worker and engine.
- [x] Add cross-engine regression test.
- [x] Run `pytest tests/unit/test_abandoned_object.py tests/integration/test_phase4_integration.py tests/integration/test_static_abandoned_pipeline.py`.

## Success Criteria

- [x] Candidate generation succeeds with YOLO returning persons only.
- [x] Intrusion/crowd engine count and behavior remain valid.
- [x] Event timestamps/durations equal media-time expectations.
- [x] Same region emits once until cleared/reintroduced.

## Risk Assessment

- High likelihood/high impact: engine signature mismatch breaks all callers. Mitigation: preserve constructor/evaluate; verified callers are worker, one unit test, and seven scripts (`app/cv/worker.py:66`; `tests/unit/test_abandoned_object.py:20`; script callers enumerated in plan validation).
- Medium likelihood/high impact: track IDs collide with region IDs. Mitigation: separate dedupe namespace; avoid pretending region IDs are YOLO tracks.
- Medium likelihood/medium impact: two state machines time the same condition. Mitigation: static detector owns persistence; event engine owns person-absence/event lifecycle only.

## Security Considerations

Continue privacy-redacted evidence path (`app/cv/evidence.py:40-60`). Never send full frames externally in this phase.

## Rollback

Set `candidate_source: tracked_classes` and restore model target classes. Contracts and detector remain dormant; no event data migration needed.

## Next Steps

Phase 04 adds optional validation and produces acceptance artifacts from existing video.
