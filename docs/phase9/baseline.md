# Phase 9 CV baseline

Captured 2026-08-14 before the unified lifecycle modules were connected to `CVWorker`.
This is characterization evidence, not a claim that Phase 8 passed.

## Frozen runtime and contract

- Detector: `app.cv.detector.DEIMv2Detector`; confidence `0.05`, NMS IoU `0.5` defaults.
- Tracker: `app.cv.tracker.ByteTrackMultiObjectTracker`; lost buffer `30`, activation `0.25`,
  minimum consecutive frames `2`, IoU `0.10`, high-confidence threshold `0.60`.
- Store: one `app.cv.track_store.TrackStore` per camera; it retains tracks and currently has
  no expiry operation. Phase 9 adapters therefore treat the list passed for the current frame
  as the active snapshot.
- Intrusion: dwell `2s`, cooldown `30s` defaults; person foot point and the existing
  `TrackIntrusionStateTracker` define entry/activation/exit.
- Crowd: count `8`, hold `10s`, release `5`, cooldown `60s` defaults; distinct person IDs only.
- Abandoned object: unchanged `kaggle_pipeline.phase7c_kernel.phase7c_core`; stationary hold
  `3s`, owner-away hold `5s`, plus its rolling-quality, stitching and association defaults.
- Public contract: `cv-event-v1`, fields and builders in `app/cv/contracts`; accepted types are
  exactly `ZONE_INTRUSION`, `CROWD_THRESHOLD`, `ABANDONED_OBJECT`; lifecycle states are exactly
  `START`, `UPDATE`, `END`. No field was renamed.

## Artifact identity and unavailable evidence

- Repository paths identify DEIMv2 config/checkpoint/backbone, but no trustworthy Phase 8
  completion artifact containing their expected SHA-256 values was found in the checked-in
  Phase 8 journal. Local weights are Git-LFS/user assets and were not read or hashed here.
- `docs/journals/260810-1125-phase8-cv-e2e-validation-gates.md` records intent only and does
  not provide a completed PASS table. Phase 8 PASS is therefore **unavailable / not inferred**.
- Focused and regression pytest results are recorded after execution below. A missing pytest
  executable/dependency must be recorded as unavailable, never converted to PASS.

## Verification commands

| Command | Result |
|---|---|
| `.venv\\Scripts\\python.exe -m compileall -q ...` | PASS; all new modules/tests compiled |
| `.venv\\Scripts\\python.exe -m pytest tests/contracts tests/unit/test_cv_event_manager.py tests/unit/test_intrusion_lifecycle_adapter.py tests/unit/test_crowd_lifecycle_adapter.py tests/unit/test_phase7c_production_adapter.py tests/unit/test_cv_worker_publisher_config.py tests/integration/test_unified_cv_baseline.py tests/integration/test_unified_cv_worker.py tests/integration/test_deimv2_worker_runtime.py tests/unit/test_phase7c_v1_core.py -q` | PASS: 37 tests, 8 subtests; 3 expected legacy-config deprecation warnings |
| `.venv\\Scripts\\python.exe -c "import ..."` | PASS after installing the minimal project test/runtime dependencies into `.venv` |
| `.venv\\Scripts\\python.exe -m pytest tests -q` | delegated to the Phase 9 tester; result recorded separately, with no PASS inferred here |

No model weight, detector threshold, tracker threshold, or rule threshold is changed by Phase 1–2.
