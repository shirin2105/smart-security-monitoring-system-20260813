# Phase 9 real-video regression

Date: 2026-08-14. Runtime: `third_party/deimv2/.python311/python.exe`, Torch
2.5.1 CUDA, production DEIMv2 checkpoint/config, ByteTrack, shared TrackStore,
three unified adapters, CVEventManager, and JsonlPublisher.

## Results

| Case | Processed / detector calls | Tracks | Output | Lifecycle | Result |
|---|---:|---:|---|---|---|
| ABODA `datasets/aboda-video1.avi` | 320 / 320 | 11 | 2 `ABANDONED_OBJECT` records | START, END; no duplicate payload | PASS |
| Phase8 Walk1 intrusion | 122 / 122 | 4 | 22 `ZONE_INTRUSION` records | valid START/UPDATE/END; no duplicate payload | PASS |
| Phase8 Meet_Crowd | 98 / 98 | 8 | 13 `CROWD_THRESHOLD` records | valid START/UPDATE/END; no duplicate payload | PASS |
| Phase8 Browse1 negative | 208 / 208 | 5 | no event | no duplicate payload | PASS |

Every persisted record passed `cv-event-v1` validation. Detector call count equals
processed frame count for every case. Each worker created one ByteTrack runtime and one
TrackStore, and passed the same immutable active snapshot to all three adapters.

ABODA emitted at media time 52.519 s inside the exploratory 48-56 s label window.
Evidence recorded stationary duration 3.170 s, owner-away duration 5.005 s,
association score 0.8746, rolling luggage quality 0.7447, owner track
`279869641600004`, and physical luggage `LUG_0001`. The source track list contains one
continuous track for this replay; the separate Phase7C fragmented-luggage regression
proves cross-track physical stitching.

## Artifacts

- `artifacts/phase9-real-video/aboda.jsonl`
- `artifacts/phase9-real-video/intrusion.jsonl`
- `artifacts/phase9-real-video/crowd.jsonl`
- Negative case emitted no JSONL because it produced zero events (expected).
- `artifacts/phase9-real-video/report.json`
- `tools/phase9/real_video_regression.py`

Video SHA-256:

- ABODA: `a4b089eddc52631421c3bb834b62de95d11ac78684a69b69305ed9299e1477db`
- Walk1: `a5d6dc7d7def01c1bdaeea8ff620195c148b366e1a52589bf4e46f15b6daa0c2`
- Meet_Crowd: `223f01cdd4c6c31121a93387cb4e39305c2f6f37254d726121f39cac3729689c`
- Browse1: `fafff382d83c7f091dc47396dee82159fb88c0d951b649b6f17afc2b0a914380`

## Test classification

- Phase9/CV tests: PASS, 78 tests plus 8 subtests.
- Full repository suite: not a Phase9 failure. Collection is blocked by optional/non-CV
  dependencies absent from the lightweight test environment (`langgraph`, `fastapi`,
  `websockets`, and related backend/agent packages).
- Webcam code: READY; 3 unit tests passed. Hardware scenarios remain USER MANUAL;
  no hardware PASS is claimed.
