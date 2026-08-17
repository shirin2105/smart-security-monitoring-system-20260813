# Session Summary

## Objective
- Simulate camera 2 as a real **continuous live camera stream**: DEIMv2 watches the looped video **paced to wall-clock** so alerts fire at the exact live moment (never pre-created); alert appears immediately with "video chưa sẵn sàng", then the evidence clip backfills; all video surfaces (tile, detail modal) show the **same live playhead** (no restart from t=0).
- Alert = real DEIMv2 inference (not pre-rendered); evidence clip cut on-the-fly `[detectedAt−20s, +3s]`; only ABANDONED_OBJECT enabled for the cam-2 demo.

## Important Details
- Two `app` packages: `back-end/app` (backend, venv = root `.venv`) and repo-root `app` (CV, venv = `.venv-deimv2` with torch). Backend fallback DB is **`back-end/security_monitoring.db`** (CWD-relative), not repo-root. `EVENT_INGEST_TOKEN=test-producer-token`.
- Ingest: `POST /api/v1/events/ingest` (Bearer token). Duplicate candidateId → DUPLICATE_IGNORED. Backfill: `POST /api/v1/events/{incident_id}/artifact-ready` (body `{uri, redactionStatus}`) → sets artifact + broadcasts `ALERT_UPDATED`; 404 missing incident; 401 unauthenticated.
- **Stream clock**: `POST /api/v1/stream/clock` (ingest auth; body `{cameraId, epoch, duration}`, pattern `^cam_[0-9]+$`, unknown camera → 422 via `CandidateReferenceError`; maps cam_02→2) + `GET /api/v1/stream/clock` (list). Backend stores in-memory per-camera `{camera_id, epoch, duration}` in `back-end/app/services/stream_clock.py`.
- `/api/v1/alerts` returns a **plain JSON array** (limit 50) — NOT `{items:[]}`.
- Mounts: `/media` → repo-root `tests/clips`; `/evidence` → `artifacts/evidence_clips`.
- Clip params in `app/cv/clip_publisher.py`: `CLIP_BEFORE_S=20.0`, `CLIP_AFTER_S=3.0`; `-an`; `_CANDIDATE_ID_SAFE = re.compile(r"[^A-Za-z0-9._-]")` (no `:` → Windows ADS bug). `post_stream_clock(camera_id, epoch)` posts `{cameraId, epoch, duration}` derived from `endpoint_url` base + Bearer token, retries 3×, prints outcome.
- Frontend real mode: `VITE_USE_MOCK=false` (only `.env.example`); frontend `localhost:8000` reaches backend `127.0.0.1:8000`. Login `guard`/`guard123`. Both servers up (5173 & 8000 HTTP 200).
- Event lifecycle: CVEvent states `START|UPDATE|END`; only START is posted. Event types logic: ZONE_INTRUSION per person×enabled-zone polygon `dwell_seconds=2`; CROWD_THRESHOLD full-frame count ≥8 held 10s, release ≤5; ABANDONED_OBJECT Phase7C = stationary luggage + owner away + quality, full-frame.
- `run_live_demo.py`: `--loops` (default **0 = forever**), `--loop-delay`; one shared `DEIMv2Detector`; **fresh `run_id` per pass → new candidate IDs → new incident each loop**. Cam-2 source `datasets/aboda-video1.avi` (73s, 640×480, ~29.97fps); per pass ~90 CVEvents, 11 START detections, 1 ABANDONED_OBJECT published.
- `frame_time_seconds(frame)` for file source = `(frame_id - 1) / source_fps` (native fps ~29.97) → seconds into the video (pacing basis).
- **Real-time pacing**: `PacedVideoSource` wraps the source; per frame sleeps `(epoch + now_s) - time.time()` → detection at video-second `s` is posted at wall `epoch + s`, i.e. exactly when the synced browser video shows it. `post_stream_clock` called at each pass start (`epoch = time.time()`).
- Frontend `LiveCameraVideo` component: fetches clock (poll every 20s to track new passes), computes playhead `(now − epoch) % duration`, seeks on `loadedmetadata`, drift-corrects every 10s (only if >1.5s off); falls back to plain loop when no clock. Used in `CameraGrid` tile + `CameraDetailModal` (both share the same live playhead). IncidentDetailPage shows the evidence clip.
- test_assessment.py has 8 pre-existing failures (naive/aware datetime at `back-end/app/services/assessment_worker.py:37`) — out of scope, pending decision.

## Work State
### Completed
- **Immediate-alert + backfill flow**: `mark_incident_artifact_ready` (service) + `artifact-ready` endpoint; publisher posts PENDING first (returns incident id), cuts clip, backfills; frontend "Video bằng chứng chưa sẵn sàng" → video appears when ready. Verified via log `Published -> 201` → `Artifact ready incidentId=N`.
- **Looping demo**: `--loops`/`--loop-delay`, shared detector, per-pass run_id → new incident per loop.
- **Live-stream simulation** (this session): `stream_clock` service + API router (registered in `main.py`); `EvidenceClipPublisher.post_stream_clock`; `PacedVideoSource` real-time pacing in `run_live_demo`; frontend `StreamClockEntry` + `getStreamClock()` (http + mock) + `LiveCameraVideo` wired into `CameraGrid` tile and `CameraDetailModal` with periodic clock refresh.
- **End-to-end verified live**: backend restarted; demo relaunched `--loops 0` (forever) paced real-time; clock registered per pass (epoch updates); pass-to-pass gap ≈ 88.7s (73s pacing + overhead) proving real-time pacing; incidents id 4,5,6 (new run) created at detected-at 53.75s + overhead with COMPLETE backfilled clips; `GET /api/v1/stream/clock` returns `{camera_id:2, epoch, duration:73.04}`; frontend 200, `/media` 200, `/evidence` 200. Pass 1 anomaly was mis-timing on my side (real elapsed ≈85s between launch & first log check) — all passes paced correctly.
- Tests green: backend **18/18** (added `test_stream_clock_register_and_list`, `test_stream_clock_requires_auth_and_valid_camera`; fixed 500→422 on unknown camera), CV **5/5**, frontend **64/64** (added `getStreamClock` mock stub; LiveCameraVideo degrades to plain loop when fetch unavailable).

### Active
- Demo running continuously in background (log `cv_live.log`, err `cv_live.err`); incidents 4,5,6 from this run; clock registered/updated per pass. Ready for user to watch the web UI (camera 2 tile/modal playhead in sync, alert fires at the live moment, clip backfills seconds later).

### Blocked
- (none) — pre-existing `test_assessment.py` datetime failures remain out of scope unless user approves.

## Next Move
1. User verifies on http://127.0.0.1:5173: camera 2 tile/modal at live playhead (no t=0 restart), alert appears at the exact live moment, clip "chưa sẵn sàng" → backfilled; incidents accumulate ~every 88s.
2. If a fresh-clean run is preferred: stop demo, delete `back-end/security_monitoring.db` + `artifacts/evidence_clips`, restart backend, relaunch demo.
3. Optional cleanup: `test_assessment.py` datetime bug decision; code review pass (per AGENTS workflow) before commit.

## Relevant Files
- `back-end/app/api/stream_clock.py`: new router POST/GET `/api/v1/stream/clock`.
- `back-end/app/services/stream_clock.py`: in-memory clock store.
- `back-end/app/main.py`: registers `stream_clock` router.
- `back-end/app/api/events_ingest.py`: ingest + `artifact-ready` + `_authenticate`.
- `back-end/app/services/ingest.py`: `mark_incident_artifact_ready`, `map_camera_id`, `CandidateReferenceError`.
- `back-end/app/db/database.py`: cam-2 seed `/media/aboda-video1.mp4`; incident ingest columns.
- `app/cv/clip_publisher.py`: PENDING-then-backfill publish; `post_stream_clock`; `-an`; clip window.
- `app/cv/run_live_demo.py`: loops, shared detector, per-pass run_id, `PacedVideoSource`, `post_stream_clock` per pass.
- `app/cv/events/frame_time.py`: `frame_time_seconds`.
- `front-end/src/api/types.ts`: `StreamClockEntry`, `getStreamClock` on `ApiTransport`.
- `front-end/src/api/httpTransport.ts` + `mock/mockTransport.ts`: `getStreamClock` impl/stub.
- `front-end/src/components/camera/LiveCameraVideo.tsx`: new playhead-synced video.
- `front-end/src/components/camera/CameraGrid.tsx` + `CameraDetailModal.tsx`: use `LiveCameraVideo`.
- `front-end/src/components/alerts/AlertSidebar.tsx`, `common/EvidenceMedia.tsx`, `api/adapters.ts`, `domain/types.ts`: "chưa sẵn sàng" state + backfilled video.
- `datasets/aboda-video1.avi` (CV source), `tests/clips/aboda-video1.mp4` (browser feed at `/media`).
- Tests: `back-end/tests/test_api.py` (18 pass), `app/cv/test_clip_publisher.py` (5 pass), `front-end` vitest (64 pass).