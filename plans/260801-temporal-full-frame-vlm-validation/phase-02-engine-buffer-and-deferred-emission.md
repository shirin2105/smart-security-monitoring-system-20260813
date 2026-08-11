---
phase: 2
title: "Engine buffer and deferred emission"
status: complete
priority: P1
effort: 4h
dependencies: [1]
---

# Phase 02: Engine buffer and deferred emission

## Context Links

- Region-state lifetime is one engine instance per worker/camera: `app/cv/worker.py:20-23,75-83`; state is created/cleared at `app/events/abandoned_object.py:184-202`.
- Current candidate maturity, synchronous validation, and emission: `app/events/abandoned_object.py:204-253`.
- Engine public entry point: `app/events/abandoned_object.py:256-258`.
- Event timestamps and IDs currently use evaluation time: `app/events/abandoned_object.py:237-250`.

## Overview

Introduce bounded camera-local sampling and a per-region pending decision so temporal validation waits until `T+8s` while preserving `T` in the emitted event.

## Requirements and Data Flow

- Every evaluated full frame enters a camera-local sampler before region branching. Default sample interval 1 second; retain only data needed for `now-8s` through newest pending `T+8s`; hard cap 17 selected frames per validation request.
- When abandonment conditions first mature, snapshot `T`, region observation, person count, absence/stationary durations, and stable candidate identity inputs. Do not mark emitted or validate yet.
- At/after `T+8s`, select nearest deterministic samples for inclusive offsets `-8..+8`, preserving order and available pre-roll. Invoke temporal validator once.
- Accepted/unavailable: build candidate with `detectedAt=T`, candidate ID timestamp from `T`, `lastSeenAt=T`, and snapshot durations/context. Rejected: terminally suppress. Region disappearance before decision must not erase an already-matured snapshot or required post-roll collection.

## Related Code Files / Ownership

- Modify only `app/events/abandoned_object.py` and `tests/unit/test_abandoned_object.py`.
- Create/delete: none.

## Implementation Steps

1. Add explicit pending-validation state to `RegionEventState`; verify it remains camera-local, not process-global.
2. Add bounded timestamp-driven full-frame sampling using copied frames so later overlays/mutation cannot corrupt history.
3. Split candidate maturity from decision readiness and candidate construction; avoid duplicate logic and duplicate calls.
4. Retain pending region snapshots when detector stops submitting the region; expire/clear after verdict or a bounded deadline.
5. Preserve immediate legacy behavior when temporal mode is disabled; gate new delay through config injected into the engine.
6. Write unit tests for exact boundaries, sparse/high FPS inputs, overlapping regions, rejected/unavailable verdicts, disappearing regions, missing images, and reset/cleanup.

## Failure Modes and Mitigations

| Failure | Likelihood x impact | Mitigation |
|---|---|---|
| Unbounded ndarray retention | High x High | timestamp pruning, copied sampled frames only, max count assertions |
| Region removed during post-roll | Medium x High | pending state independent from active-region cleanup |
| Frame cadence misses exact second | High x Medium | deterministic nearest sample per target offset, monotonic de-duplication |
| Multiple regions mature together | Medium x Medium | share camera buffer; independent pending/verdict cache keyed by region |
| stream ends early | Medium x Medium | no partial temporal verdict/event; cleanup on engine teardown/reset |

## Test Matrix

| Unit case | Assertion |
|---|---|
| candidate at `T` | zero validator calls through `T+7.999`; one at `T+8` |
| 1 FPS history | ordered timestamps `T-8..T+8`, count 17 |
| insufficient pre-roll | all available ordered frames, count <=17 |
| accepted/unavailable | one event; `detectedAt`, ID token, `lastSeenAt` use `T` |
| rejected | no event; no retry |
| second region | shared frames, isolated state/verdict |

## Compatibility, Security, Rollback

- `evaluate`, `submit_static_regions`, and `EventCandidate` remain unchanged. Default temporal-off keeps current synchronous behavior.
- Raw frames stay memory-only; evidence persistence continues existing redacted single-frame path at `app/cv/evidence.py:16-60`.
- Rollback disables temporal config, then removes pending/buffer state without data migration.

## Success Criteria

- [x] Validation never occurs before `T+8s` in temporal mode.
- [x] Request frames are ordered, full-scene, sampled near 1 FPS, maximum 17.
- [x] Candidate timestamp/context remain the maturity snapshot, not decision-frame values.
- [x] Memory/state are bounded and cleared deterministically.

## Next Steps

Phase 03 wires production configuration and proves the demo uses the same engine path.

## Unresolved Questions

None.
