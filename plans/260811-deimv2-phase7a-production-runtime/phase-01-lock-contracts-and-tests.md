---
phase: 1
title: "Lock contracts and tests"
status: completed
priority: P1
effort: 3h
dependencies: []
---

# Phase 1: Lock contracts and tests

## Context Links

- Runtime call path: `app/cv/worker.py:85-123`
- Stable schemas: `app/common/schemas.py:8-31`
- Existing detector behavior to replace: `app/cv/detector.py:13-69`
- Existing tracker behavior to replace: `app/cv/tracker.py:28-88`
- Reuse reference: `devtools/webcam_cv_test/model_runtime.py:21-133`
- Shared detector supervisor: `app/cv/multi_camera_runner.py:15-56`

## Overview

Write tests first for the narrow production contract. Freeze input/output and failure semantics before touching runtime code.

## Requirements

- `detect(FrameData) -> tuple[list[DetectionResult], float]` remains callable by `CVWorker` (`app/cv/worker.py:96-100`).
- `track(list[DetectionResult], FrameData) -> list[TrackResult]` remains callable by `CVWorker` (`app/cv/worker.py:99-106`).
- Runtime classes: Phase 7A raw IDs `0=person, 1=backpack, 2=handbag, 3=suitcase`; production normalized names remain `person`, `luggage`.
- `TrackResult.track_id` is globally unique across the two class-specific trackers and stable across frames.
- No changes to `EventCandidate` or publishing (`app/common/schemas.py:64-87`, `app/cv/worker.py:108-115`).

## Architecture and Data Contracts

| Input | Transform | Output | Failure |
|---|---|---|---|
| `FrameData.image` BGR ndarray | BGR->RGB, resize/tensor transform, DEIM postprocess | raw boxes/scores/labels | `None` image returns empty results; malformed ndarray raises typed/value error |
| raw IDs 0..3 | threshold + cross-class luggage merge/NMS | `DetectionResult(person|luggage)` | unknown IDs discarded and counted/logged |
| detections + media timestamp | one ByteTrack instance per normalized class | `TrackResult` | invalid bbox/confidence rejected; empty frames still update both trackers |
| tracker observation | timestamp conversion | ISO `first_seen_at`/`last_seen_at` | source timestamp remains canonical; no wall-clock fallback |

Do not reuse `CandidateManager` from `model_runtime.py:44-49`: existing production event engines already own eligibility and event state. Duplicating it would silently filter tracks before those engines.

## Related Code Files — Exclusive Ownership

- Create `tests/unit/test_deimv2_detector.py`: loader, mapping, filtering, latency, failure tests.
- Create `tests/unit/test_bytetrack_tracker.py`: isolation, ID namespace, time, empty update, validation tests.
- Create `tests/integration/test_deimv2_worker_runtime.py`: worker seam and publisher regression test.
- Read only: production/runtime reference files listed above.

## Tests Before

1. Detector construction with missing checkpoint/backbone/config raises `FileNotFoundError` naming the missing path.
2. Checkpoint without `ema.module` or `model`, and strict state mismatch, fail construction; no partial model allowed.
3. Synthetic model output verifies raw person is preserved and three luggage classes normalize to one class using the webcam merge semantics (`devtools/webcam_cv_test/model_runtime.py:104-112`).
4. Confidence threshold boundary, empty output, unknown class, invalid box, and `image=None` behavior.
5. ByteTrack creates exactly two tracker instances, updates both on every processed frame, prevents cross-class matching, and namespaces IDs as verified in parent `phase7b1_runtime_core.py:132-215`.
6. Timestamps and first-seen state survive matches and missed frames; reset/lifetime is per `CVWorker`, not process-global.
7. Worker passes detections to tracker once and unchanged tracks to `TrackStore`; publisher receives existing `EventCandidate` shape.

## Test Matrix

| Level | Scenarios | Observable pass |
|---|---|---|
| Unit | asset validation, strict load, transform, threshold, mapping, NMS, latency | deterministic fake-tensor/model tests; no GPU required |
| Unit | two class trackers, IDs, empty frames, reset, invalid inputs | exact IDs/classes/timestamps asserted |
| Integration | worker detector->tracker->store->engine->publisher | existing candidate schema and publish count unchanged |
| Regression | all current unit/integration tests | no backend/frontend or existing CV failures |

## Implementation Steps

1. Add tests using injected model loader/postprocessor/tracker factories. Mock only external compute boundaries; use real contract objects and transformations.
2. Confirm tests fail because DEIM/ByteTrack production implementations do not exist.
3. Record exact expected exceptions and log fields; avoid assertions on incidental message formatting beyond missing asset path/type.

## Success Criteria

- [x] New tests fail for missing implementation, not test setup defects.
- [x] Every contract and failure row above has at least one assertion.
- [x] Tests do not require Phase 7A weights, CUDA, camera hardware, network, backend, or frontend.
- [x] Existing tests still run unchanged.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---:|---:|---|
| Tests reproduce webcam internals instead of behavior | M | H | Assert public contracts and small golden tensors only |
| Tracker mocks hide API mismatch | M | H | Add one dependency smoke test in Phase 3 with installed libraries |
| Timestamp semantics drift | M | H | Explicit multi-frame tests using `FrameData.captured_at` |

## Rollback

Delete the three newly added test files. No production state or dependency changes.

## Next Steps

Phase 2 starts only after test failures are reviewed and the contracts above are accepted.
