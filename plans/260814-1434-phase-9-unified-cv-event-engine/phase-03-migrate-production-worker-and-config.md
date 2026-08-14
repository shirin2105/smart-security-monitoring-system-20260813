---
phase: 3
title: "Migrate production worker and config"
status: completed
priority: P1
effort: 1.5d
dependencies: [2]
---

# Phase 3: Migrate production worker and config

## Overview

Switch CVWorker from static-region/VLM abandoned logic to the unified engine while retaining legacy config temporarily for reversible rollout.

Progress: complete. Production worker/config use the unified path. `CVEventPublisher.publish(CVEvent)` is the verified final CV boundary; `JsonlPublisher` is canonical. Backend endpoint NOT REQUIRED.

## Implementation Tracking

- [x] Unified adapters and event manager wired per worker.
- [x] Phase7C config validation and ignored-legacy warning path implemented.
- [x] Unified worker integration tests included in final 78 + 8 passing result.
- [x] Required post-fix CV suite and 4/4 real-video path verified.
- [x] Production publisher boundary verified end to end; backend compatibility endpoint explicitly not required.

## Architecture / Data Flow

`source → sampler → detector once → tracker once → update TrackStore once → immutable active snapshot → 3 adapters → manager → validate → existing publisher`. Preserve cleanup boundary at `app/cv/worker.py:103-147` and publisher contract at `app/cv/worker.py:89-96`.

## Related Code Files / Exclusive Ownership

- Modify: `app/cv/worker.py`, `app/cv/multi_camera_runner.py`, `app/cv/demo_flow.py`, `app/cv/continuous_demo.py`.
- Modify: `configs/event_rules.yaml`, `configs/phase7c_cameras.example.json`, `configs/cv-web-demo.yaml`.
- Modify caller tests: `tests/integration/test_deimv2_worker_runtime.py`, `test_intrusion_pipeline.py`, `test_phase3_integration.py`, `test_phase4_integration.py`, `test_temporal_worker_eos.py`; `tests/unit/test_cv_worker_publisher_config.py`.

## Implementation Steps

1. Add Phase7C production config first; validate types/ranges and defaults from frozen baseline.
2. Instantiate one manager and three adapters per worker; inject seams for tests.
3. Delete worker execution of `StaticRegionDetector.update/submit_static_regions` but do not delete modules/config yet.
4. Publish only validated CVEvent v1. If existing publisher still requires EventCandidate, add a CV-local compatibility adapter; do not change backend.
5. Warn once for ignored legacy abandoned/VLM keys during transition; never log credentials.
6. Ensure source release and manager/adapter finalization on detector failure, stop, timeout, EOS.

## Tests / Success Criteria

- [x] Detector call count equals processed frame count; tracker/store update once; same snapshot object passed to three adapters.
- [x] Existing `CVWorker(...)` construction sites compile after signature compatibility.
- [x] Invalid Phase7C config fails before frames; old keys do not activate VLM.
- [x] Worker interruption/EOS/failure releases source and emits deterministic END where valid.

## Risks / Rollback / Compatibility

- High × High: publisher/backend expects EventCandidate, not CVEvent. Mitigation: freeze boundary in Phase 1; CV-only compatibility serialization, no backend edits.
- Medium × High: multi-camera shared detector vs per-worker manager state leak. Mitigation: detector may remain shared/locked; tracker/store/manager stay camera-local; two-camera isolation test.
- Rollback: revert worker/config/caller-test commit; legacy modules still present and config remains readable.

## Next Steps

Phase 4 gates completed; cleanup subsequently authorized.
