---
phase: 3
title: "Integrate, configure, and validate"
status: completed
priority: P1
effort: 3h
dependencies: [2]
---

# Phase 3: Integrate, configure, and validate

## Context Links

- Worker construction/call flow: `app/cv/worker.py:18-55`, `app/cv/worker.py:85-123`
- Shared detector construction: `app/cv/multi_camera_runner.py:25-46`
- Current accidental model config: `configs/models.yaml:1-6`
- Current dependencies: `requirements.txt:8-12`
- Image packaging: `Dockerfile:1-27`
- Existing supervisor regression: `tests/unit/test_multi_camera_runner.py:6-27`

## Overview

Wire the production runtime, pin/provision dependencies and assets, and validate the narrow runtime replacement without changing ingest/backend/frontend.

## Requirements

- Both direct `CVWorker` and `MultiCameraRunner` construct the same detector configuration.
- Tracker remains per worker/camera; detector may be shared but calls must be serialized until throughput is measured.
- Config names describe DEIMv2 paths/settings; no YOLO defaults or model-version literals remain in active CV event production paths.
- Dependency strategy is reproducible on Python 3.11 CPU and CUDA deployment variants.
- Deployment does not rely on files outside repository/container/mounted artifact root.

## Related Code Files — Exclusive Ownership

- Modify `app/cv/worker.py`: import/construct DEIM detector and ByteTrack tracker; keep source/engine/publisher flow unchanged.
- Modify `app/cv/multi_camera_runner.py`: use one shared lock-protected DEIM detector and pass the locked adapter, not its unlocked private object, to workers.
- Modify `configs/models.yaml`: DEIM source/config/checkpoint/backbone, device, threshold, NMS settings, stable model version.
- Modify `requirements.txt`: remove Ultralytics; add pinned/compatible torch, torchvision, Pillow, supervision, and ByteTrack provider dependencies based on the verified webcam environment.
- Modify `Dockerfile`: provision model source/artifact contract or mount validation; do not bake unavailable parent absolute paths.
- Modify `app/events/intrusion.py`, `app/events/crowd.py`, `app/events/abandoned_object.py`: replace hard-coded YOLO model-version strings only; no rule behavior changes (`app/events/intrusion.py:92-110`, `app/events/crowd.py:143-160`, `app/events/abandoned_object.py:452-470`).
- Modify `app/common/schemas.py`: change only the default `modelVersion` if still reachable without explicit engine value (`app/common/schemas.py:64-84`).
- Modify `tests/unit/test_multi_camera_runner.py`: assert workers receive the locked detector facade and concurrent calls serialize.
- Modify the Phase 1 integration test as needed for final constructor names.
- Modify `docs/system-architecture.md`: runtime/assets/failure/rollback disclosure.
- No changes under `back-end/` or `front-end/`.

## Dependency and Setup Strategy

1. Treat parent `model-CV-v1` files as the verified source: DEIM repository, `vitt_distill.pt`, Phase 7A `best.pth`, Phase 7B.1 tracker core.
2. Port code into tracked production modules. Do not import `devtools/`, `kaggle_pipeline/`, or an adjacent worktree at runtime.
3. Choose one deploy contract:
   - preferred: source copied/vendor-pinned under `third_party/deimv2`, large weights mounted read-only under a configured artifact root;
   - acceptable for an internal image: both source and checksum-pinned weights copied during an authenticated build.
4. Record expected SHA-256 for checkpoint and backbone. Startup verifies path, then checksum when configured.
5. Use environment/config overrides for deployment paths; repository defaults point to repository-relative locations only.
6. Pin exact tracker ecosystem versions proven by the webcam environment (`trackers==2.5.0.post0` is documented at `devtools/webcam_cv_test/requirements_test.txt:3`). Resolve and lock compatible `supervision`, torch, torchvision versions; do not use unbounded minimums for native ML runtime.
7. Keep CPU installation possible. CUDA wheels/image selection belongs to deployment build configuration, not runtime downloads.

## Data Flow Verification

Trace required after edit:

1. `CVWorker.run` receives `FrameData` from unchanged source.
2. Locked/shared detector produces application `DetectionResult` objects.
3. Camera-local tracker produces `TrackResult` objects.
4. Existing `TrackStore` and event engines consume them unchanged.
5. Existing publisher produces the same ingest request; backend and frontend are untouched.

## Implementation Steps

1. Re-grep all constructor callers and all YOLO/Ultralytics/model-version strings; enumerate every result before edits.
2. Centralize detector config parsing in one factory/helper used by worker and supervisor; DRY defaults.
3. Fix shared locking flow: currently supervisor passes `self.detector._detector` to workers (`app/cv/multi_camera_runner.py:44-47`), bypassing `LockedDetector.detect` (`app/cv/multi_camera_runner.py:15-22`). Pass the facade itself.
4. Replace tracker construction with camera-local ByteTrack adapter using source FPS/inference cadence explicitly; document chosen `frame_rate` meaning and test it.
5. Update model config and hard-coded metadata; do not alter event thresholds or schemas.
6. Pin dependencies and define source/weight provisioning. Build/import smoke test on clean environment.
7. Run targeted then full regression suites; perform one real-asset CPU or CUDA smoke frame if assets are locally provisioned.
8. Update architecture doc with asset checksums, failure behavior, and operational disclosure.

## Test Matrix / Regression Gates

| Gate | Command / validation | Pass condition |
|---|---|---|
| Static | `python -m compileall app tests` | zero syntax/import compilation failures |
| Targeted unit | `pytest -q tests/unit/test_deimv2_detector.py tests/unit/test_bytetrack_tracker.py tests/unit/test_multi_camera_runner.py` | all pass |
| Integration | `pytest -q tests/integration/test_deimv2_worker_runtime.py` | unchanged publisher/event shape |
| Full Python | `pytest -q` | all existing tests pass; unrelated pre-existing failures separately evidenced |
| Dependency smoke | clean Python 3.11 install + imports | exact pinned stack imports together |
| Asset smoke | instantiate + infer one non-square frame | strict load succeeds, finite outputs/latency, no YOLO import |
| Contract grep | YOLO/Ultralytics and parent absolute paths | no active production references |
| API/UI boundary | git diff path audit | no `back-end/` or `front-end/` changes |

## Success Criteria

- [x] Direct worker and multi-camera paths use DEIMv2 Phase 7A plus ByteTrack.
- [x] Shared model calls are serialized; tracker state is isolated per camera.
- [x] Verified Python 3.11 environment imports the exact pinned runtime stack.
- [x] Run startup rejects missing, untrusted, or incompatible assets before reading frames; the shared multi-camera owner remains eager.
- [x] One real checkpoint smoke inference passes on an available supported device.
- [x] Full tests pass and backend/frontend files are unchanged.
- [x] Runtime metadata says the actual DEIMv2 model version.
- [x] Legacy worker tests inject deterministic detectors; config/backbone paired override is documented and tested.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---:|---:|---|
| Weights/source excluded from Git/Docker context | H | H | explicit mount/build contract + startup preflight + clean-image smoke |
| Torch/CUDA wheel incompatibility inflates/breaks image | H | H | separate CPU/CUDA lock/build strategy; test clean image |
| Supervisor lock accidentally bypassed | H | H | pass facade; concurrency test measures max in-flight inference = 1 |
| Event confidence/model metadata semantics change | M | M | keep schemas; assert exact candidate payload in integration test |
| Removing Ultralytics breaks unrelated imports | M | M | full `rg` caller inventory and full suite before removal |

## Backwards Compatibility

- No data migration. Stored candidates remain readable because schema fields and enum values do not change.
- Existing injected detector test doubles remain structurally accepted (`detect` protocol).
- Config change is intentionally breaking only for obsolete YOLO runtime keys; document old-to-new mapping and fail on unknown/old keys rather than silently defaulting.
- Backend ingest and frontend require no deployment coordination beyond receiving truthful `modelVersion` text.

## Rollback

1. Stop CV workers; backend/frontend can remain running.
2. Revert Phase 3 wiring/config/dependencies/docs and Phase 2 runtime files as one atomic release.
3. Restore prior image/config artifact. No database rollback.
4. Run former supervisor/worker smoke tests before restarting CV workers.
5. If DEIM fails for one camera at runtime, supervisor reports that camera failed; do not automatically fall back to YOLO or empty detections.

## Known Limitation

- Coverage metrics unavailable because the compatible QA environment lacks `coverage`/`pytest-cov`; non-blocking because all specified functional, regression, asset, and review gates passed.

## Unresolved Questions

- None.
