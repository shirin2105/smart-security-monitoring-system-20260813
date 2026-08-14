# Phase 9 final CV report

Date: 2026-08-14. Scope: CV only. Backend, LLM, and Phase 10 unchanged.

## Merge readiness

| Gate | Status | Evidence |
|---|---|---|
| Unified worker | PASS | One DEIMv2 call/frame, ByteTrack, one shared immutable TrackStore snapshot, three adapters |
| Real-video regression | PASS | ABODA, Walk1 intrusion, Meet_Crowd, Browse1 negative |
| Phase7C regression | PASS | ABODA START/END at 52.519 s; owner-away/stationary evidence; stitching tests |
| CV-related tests | PASS | 78 tests + 8 subtests |
| CVEvent v1 output | PASS | Every persisted video record schema-valid |
| JsonlPublisher | PASS | Canonical local sink; synchronized concurrent append test |
| Backend endpoint | NOT REQUIRED | Final CV boundary is `CVEventPublisher.publish(CVEvent)` |
| Webcam code | READY | 3/3 devtool tests |
| Webcam hardware | USER MANUAL | Agent made no hardware PASS claim |
| Active VLM/static-region path | REMOVED | Unified worker/config have no active import or setting; retained code/docs marked LEGACY |
| Stale YOLO active path | REMOVED | Production detector remains DEIMv2; no active Ultralytics/StrongSORT path |

## Production boundary and reliability

`CVWorker` defaults to `JsonlPublisher` and emits only `cv-event-v1`. Legacy
`EventCandidate` publishers remain isolated from `CVEventPublisher`. Lifecycle IDs
include a run-unique component, so worker restarts cannot collide in append-only JSONL.
Concurrent camera publishers targeting one path share a lock. A failed START publish is
rolled back, cleanup cannot emit an orphan END, the primary processing exception is
preserved, and source release remains unconditional.

## Real-video results

| Clip | Frames / detector calls | Tracks | Events | Result |
|---|---:|---:|---:|---|
| ABODA `aboda-video1.avi` | 320 / 320 | 11 | 2 abandoned | PASS |
| Phase8 `Walk1.mpg` | 122 / 122 | 4 | 22 intrusion | PASS |
| Phase8 `Meet_Crowd.mpg` | 98 / 98 | 8 | 13 crowd | PASS |
| Phase8 `Browse1.mpg` | 208 / 208 | 5 | 0 | PASS |

No exact duplicate payload or invalid lifecycle was found. Full hashes, event evidence,
and artifact paths are in `reports/phase9-real-video-regression.md` and
`artifacts/phase9-real-video/report.json`.

## Test classification

- TEST FAILURE: none in the required Phase 9 CV suite.
- ENVIRONMENT / OPTIONAL DEPENDENCY MISSING: full-repository collection requires
  non-CV packages including `langgraph`, `fastapi`, and `websockets`. No bulk install
  was performed to force unrelated backend/agent tests green.
- Compile: PASS for CV, publisher, Phase7C, webcam devtool, and regression runner.

## Webcam manual command and checklist

```powershell
third_party\deimv2\.python311\python.exe devtools\webcam_cv_test\app.py
# Use --camera 1 when the default camera is not the intended device.
```

- Intrusion: enter and hold in the right half.
- Crowd: show at least two people and hold long enough to trigger.
- Abandoned: exercise Phase7C stationary luggage plus owner-away behavior.
- Confirm valid START/UPDATE/END JSONL, no duplicate lifecycle, then clear and re-enter.

## Legacy classification

The unified worker, event adapters, detector/tracker, active event rules, and canonical
publisher contain no active VLM, static-region, YOLO/Ultralytics, or StrongSORT route.
Historical static-region/VLM engines, demos, tests, journals, and product documents are
retained only where still imported/tested and are labeled LEGACY in current architecture.
`app.config.llm_model` is LLM scope and was deliberately not changed.

## Unresolved questions

None for CV merge readiness. Webcam hardware verification remains assigned to the user.
