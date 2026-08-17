# Plan: Live CV over demo clip + 20s→3s evidence clip

**Goal (from user):** Replace the frontend hardcoded prerendered alert (CameraGrid fires at t=13.75s) with the real DEIMv2 model running LIVE over the demo clip during playback, emitting real-time alerts (WebSocket), and each alert's detail shows a standalone cut video clip from `detectedAt-20s` → `detectedAt+3s` (generated via ffmpeg). Source video = existing demo clip `camera-1-aboda-tracking.h264.mp4`.

## Blast radius (verified)
- Frontend: `front-end/src/components/camera/CameraGrid.tsx`, `DashboardPage.tsx`, `api/index.ts` (demo fn), `api/adapters.ts`, `components/common/EvidenceMedia.tsx`, `App.test.tsx`.
- Backend: `back-end/app/db/models.py` (Incident), `services/ingest.py`, `api/alerts.py`, `api/events_ingest.py` (already accepts detectedAt+artifact), `main.py` (static mount).
- CV: new `app/cv/run_live_demo.py` (file-source runner) + `app/cv/clip_publisher.py` (CVEvent→EventCandidateIn + ffmpeg clip).

## Steps

### 1. Backend — persist detection time + artifact
- `models.py` Incident: add `detected_at` (DateTime, nullable), `artifact_url` (String 2048, nullable), `redaction_status` (String 20, default 'PENDING').
- `ingest.py` `ingest_event_candidate`: read `payload["detectedAt"]` + `payload.get("artifact")`; set `incident.detected_at`, `incident.artifact_url`, `incident.redaction_status`. In `_incident_payload` add `detected_at`, `artifact_url`, `redaction_status`.
- `alerts.py` `IncidentResponse`: add same 3 fields; `get_incidents` includes them.

### 2. Backend — serve generated evidence clips
- `main.py`: mount `artifacts/evidence_clips` at `/evidence` (StaticFiles), mirroring the `/media` mount.

### 3. CV — live file runner + ffmpeg clip + ingest
- `app/cv/clip_publisher.py`:
  - `extract_clip(src_mp4, detected_at_s, out_path)`: `subprocess` ffmpeg `-ss max(0, detected_at_s-20) -to detected_at_s+3` (clamp end to clip duration); output mp4.
  - `to_event_candidate(cvevent, video_epoch, clip_url)`: build `EventCandidateIn` dict with `detectedAt`/`firstSeenAt`/`lastSeenAt` from `event_time_s` (video timeline), `artifact={available:True, contentType:"video/mp4", redactionStatus:"COMPLETE", uri: clip_url}`.
  - POST to `/api/v1/events/ingest` with `Bearer $EVENT_INGEST_TOKEN` (reuse `HttpPublisher` auth pattern).
- `app/cv/run_live_demo.py`: feed `MP4VideoSource(sample_clip)` → `CVWorker`/`runtime`; on each emitted `CVEvent` (START), compute `detected_at_s`, generate clip, POST candidate. Deterministic `candidateId` per (clip,camera,event).

### 4. Frontend — drop hardcoded trigger, show real alerts + clip
- `CameraGrid.tsx`: remove `CAMERA_ONE_ABANDONED_AT_S`, `syncCameraOneTimeline`, `onCameraOneAbandoned` prop + `onTimeUpdate`. Keep `<video>` tile (no scripted alert).
- `DashboardPage.tsx`: drop `onCameraOneAbandoned` + `triggerCameraOneAbandonedDemo` import.
- `api/index.ts`: remove `triggerCameraOneAbandonedDemo` (now unused).
- `api/adapters.ts` `toEvent`: `detectedAt = normalizeTimestamp(raw.detected_at ?? raw.created_at)`; map `artifact_url`+`redaction_status` (already does); add optional `clipStartS`/`clipEndS` from `raw.clip_start_s`/`clip_end_s`.
- `EvidenceMedia.tsx`: already plays standalone video; ensure it autoplays/controls when used in `IncidentDetailPage` detail (pass `autoPlay`/`controls`).

### 5. Tests
- Update `App.test.tsx` (relies on t=13.8 trigger) → drive from a mocked real `SecurityEvent` with `artifact.url` set; assert evidence video renders. Keep WebSocket/`useAlertStream` behavior intact.
- Add backend test: ingest with `detectedAt`+`artifact` persists and returns fields.
- Add `clip_publisher` unit test for ffmpeg arg clamping (negative start → 0; end clamps to duration).

## Acceptance criteria
1. Running `python -m app.cv.run_live_demo` (backend up, same `EVENT_INGEST_TOKEN`) emits a real `NEW_ALERT` over `/ws/alerts` for the demo clip with `detectedAt` = video time (~13.75s) and `artifact_url=/evidence/<id>.mp4`.
2. The generated clip is a standalone mp4 covering `[max(0,13.75-20), 13.75+3]` = `[0, 16.75]s`.
3. Frontend Dashboard no longer fires a scripted alert; alerts arrive from real WebSocket events.
4. Incident detail plays the cut evidence clip (EvidenceMedia) with redaction COMPLETE.
5. No regressions: existing backend ingest/duplicate logic, WebSocket broadcast, frontend `toEvent` for old incidents (no artifact → undefined).

## Risks
- `create_all` won't add columns to an existing `incidents` table → dev must recreate DB volume (acceptable for demo).
- VFR/h264 PTS drift: clip uses ffmpeg `-ss`/`-to` on the same file the model read; acceptable for demo. Validate clip duration in test.
- DB migration: none (no Alembic); document DB recreate.

## Out of scope (YAGNI)
- Browser-side model inference (DEIMv2 stays backend GPU).
- Multi-camera live RTSP changes (Phase 10B already real-time).
- Redaction pipeline (clip marked COMPLETE directly).
