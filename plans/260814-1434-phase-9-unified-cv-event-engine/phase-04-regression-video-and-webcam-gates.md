---
phase: 4
title: "Regression, video, and webcam gates"
status: completed
priority: P1
effort: 2d
dependencies: [3]
---

# Phase 4: Regression, video, and webcam gates

## Overview

Prove migration through automated regression and real media. This phase is the hard cleanup gate.

Progress: complete. Required Phase 9 CV suite **78 passed + 8 subtests**; real video **4/4 PASS**; webcam devtool **3/3**, hardware validation USER MANUAL.

## Gate Tracking

- [x] Required Phase 9 CV automated regression: 78 passed + 8 subtests.
- [x] Required real video regression: 4/4 PASS.
- [x] Webcam code gate: 3/3 devtool tests; hardware USER MANUAL.
- [x] Cleanup authorization: issued from required automated + video PASS.

## Related Code Files / Exclusive Ownership

- Create: `tests/integration/test_unified_cv_worker.py`, `tests/regression/test_phase9_phase7c_production.py`, `tests/integration/test_phase9_video_regression.py`.
- Modify dev-only: `devtools/webcam_cv_test/webcam_event_adapter.py`, `webcam_runner.py`, `config.json`, and tests under `devtools/webcam_cv_test/tests/`.
- Create evidence: `reports/phase9-video-regression.md`, `reports/phase9-webcam-regression.md`.

## Execution / Test Matrix

| Level | Required scenarios | Gate |
|---|---|---|
| Unit | contract, lifecycles, manager ID/dedup, TrackStore, Phase7C core | all pass |
| Integration | once/frame, shared snapshot, three CVEvent v1 outputs, JSON, START/END, EOS/error cleanup | all pass |
| Regression | known Phase7C positive; false static person filtered; physical luggage stitching | expected event/count/identity |
| Video | known ABODA/Phase7C + available Phase8 clips | no duplicate; abandoned through production worker; output schema-valid |
| Webcam | intrusion; crowd threshold=2; abandoned realtime; unified JSON; release | PASS or `NOT HARDWARE VERIFIED` with reason |

## Implementation Steps

1. Run focused suites, then full suite; retain commands/results and artifacts.
2. Replay frozen clips twice; assert deterministic lifecycle keys/IDs within each run and no duplicate alerts.
3. Verify wall-clock independence using media timestamps.
4. Run webcam devtool only; ensure UI stays outside production. Exercise stop/failure and camera release.
5. Re-grep active runtime for VLM/static-region/YOLO; capture inventory for Phase 5, but delete nothing here.

## Success Criteria

- [x] All required CV automated gates pass with no ignored failures or fake/mocked real-media claims.
- [x] Video evidence includes source/hash/config/event JSON and duplicate count=0.
- [x] Webcam evidence truthfully records READY code and USER MANUAL hardware validation.
- [x] Explicit cleanup authorization recorded: `REGRESSION PASS`.

## Risks / Rollback

- High × High: unavailable Phase8 assets/hardware. Mitigation: block video gate when required assets absent; webcam alone may use documented limitation, video may not.
- Medium × High: nondeterministic ByteTrack/model output. Mitigation: compare contract/lifecycle invariants and frozen tolerance, not brittle bbox exactness.
- Rollback: tests/evidence only; failure triggers Phase 2/3 fix, never Phase 5.

## Next Steps

Phase 5 completed after automated + video regression PASS. Webcam limitation documented.
