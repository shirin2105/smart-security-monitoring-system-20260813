---
title: "Camera 3 live webcam feed"
description: "Replace camera #3's demo video on the web with a live laptop webcam feed now; enable a real RTSP camera later, reusing Phase 10's source pipeline."
status: completed
priority: P1
effort: "11h"
tags: [camera, webcam, live, cv, frontend, rtsp]
created: 2026-08-17
blockedBy: [260814-2000-phase-10-rtsp-cctv-source-pipeline]
---

# Camera 3 live webcam feed

## Overview

Camera #3 (`Camera Hàng Rào Tây`) is already shown on the web grid but is fed by a
demo video/image. The goal is to make that tile show a **live laptop webcam** feed
now, and later swap in a **real RTSP camera** without re-architecting.

The web already supports a live non-video preview: `front-end/src/components/camera/CameraGrid.tsx:90-106`
renders any `previewUrl` that is **not** `.mp4/.webm/.avi` as a live `<img>` (no
`<video>`/stream-clock needed). So the only backend-facing change is to give camera
#3 a live MJPEG `previewUrl`; the CV side reuses the completed **Phase 10** RTSP/CCTV
source pipeline (`260814-2000-phase-10-rtsp-cctv-source-pipeline`).

## Goals

| # | Goal | Priority |
|---|------|----------|
| 1 | Laptop webcam appears as a live feed on camera #3 tile (no demo video) | P1 |
| 2 | Webcam stream served by a dedicated, CORS-enabled MJPEG server (single device owner) | P1 |
| 3 | Later: swap camera #3 to a real RTSP camera reusing Phase 10 `RTSPVideoSource` | P2 |
| 4 | Deferred: CV detection runs only on the real RTSP camera (GPU host); laptop webcam is display-only now | P3 |

## Architecture

```
laptop webcam (device 0)
        │  (single owner)
        ▼
app/webcam_stream_server.py  ──MJPEG (multipart/x-mixed-replace)──►  http://<host>:<port>/cameras/3/stream
        │                                                                   │
        │                                              CameraGrid ▸ LiveCameraVideo ▸ <img src=...>
        │                                                   (renders non-video previewUrl as live)
        ▼
[Later] Real RTSP camera: RTSPVideoSource (Phase 10) -> unified CVWorker -> CVEvent v1
       (CV detection deferred to the real camera; laptop webcam is display-only for now)
```

Key design rule: **the webcam device has one owner** — the MJPEG server. The laptop
webcam is display-only; no CV processing opens it a second time. When the real RTSP
camera is connected, Phase 10's `RTSPVideoSource` processes it directly.

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | [Phase 1: Webcam MJPEG stream server](./phase-01-start.md) | Completed |
| 2 | [Phase 2: Wire camera 3 web tile to live webcam](./phase-02-wire-camera-3-web-tile-to-live-webcam.md) | Completed |
| 3 | [Phase 3: Real RTSP camera swap and CV detection](./phase-03-real-rtsp-camera-swap-and-cv-detection.md) | Completed |
| 4 | [Phase 4: Run guide and verification](./phase-04-run-guide-and-verification.md) | Completed |

## Success Criteria

- [x] Camera #3 tile shows the live laptop webcam (motion visible, not a looping demo).
- [x] Stopping the webcam server makes the tile show the OFFLINE/"no signal" state, not a stale frame.
- [x] `SourceBadge` for camera #3 reads `CV thật` (LIVE), not `Nguồn giả lập`.
- [x] No second `cv2.VideoCapture` opens the same webcam device concurrently.
- [x] Later: setting `source_type: RTSP` + an RTSP URL on camera #3 switches it to the real camera with zero code changes in the worker.

## Open Questions

_Resolved in validation session 1:_
- **Backend mode:** primary target is the real backend seed at `back-end/app/db/database.py:90`
  (mock `fixtures.ts` kept as secondary path).
- **CV detection:** display-only on the laptop webcam now; CV runs on the real RTSP camera
  later (Phase 10 path). No `WEBCAM` badge literal — reuse `LIVE` (`CV thật`).
- **Seed apply:** delete the SQLite DB file and restart backend so `init_db_and_seed()`
  recreates camera #3 with the new values.

## Validation Log

### Verification Results (Step 2.5 — Standard tier, 4 phases)
- Claims checked: 10
- Verified: 10 | Failed: 0 | Unverified: 0
- Tier: Standard (Fact Checker + Contract Verifier)
- Key claims verified against code:
  - `CameraGrid.tsx:90-106` renders non-video `previewUrl` as `<img>` (MJPEG-safe). VERIFIED.
  - `toCamera` maps `source==='CV' → 'LIVE'` (`adapters.ts:179`). VERIFIED.
  - `create_video_source` selects `RTSPVideoSource` for `RTSP/CAMERA/LIVE` (`factory.py:19`). VERIFIED.
  - `RTSPVideoSource` exists and is completed via Phase 10. VERIFIED.
  - `LIVE_SOURCE_TYPES` defined in `worker.py:30`. VERIFIED.
  - Backend seed for camera #3 is `back-end/app/db/database.py:90`
    (`stream_url="/media/pets2006_3.mp4"`, `source="SIMULATOR"`, `status="warning"`). VERIFIED
    (the plan's earlier "find the seed script" placeholder is now pinned to this exact line).
  - `SourceType` union is `'SIMULATED' | 'LIVE'` (`domain/types.ts:35`) — confirms reusing
    `LIVE` is the minimal path; no union change needed. VERIFIED.
- Failures: none.

### Interview (Step 4) — 3 questions, all recommended options chosen
1. Badge label → **Reuse `LIVE` (`CV thật`)**; no `WEBCAM` union/badge change.
2. CV on laptop webcam → **Display-only now**; CV deferred to real RTSP camera.
3. Seed apply → **Delete DB + reseed** (seed runs only when tables empty).

### Propagation (Step 6)
- Phase 2: dropped `domain/types.ts`, `adapters.ts`, `Badges.tsx` WEBCAM edits; pinned seed
  target to `database.py:90`; added DB-reseed step; mock `fixtures.ts` uses `sourceType:'LIVE'`.
- Phase 3: reframed to RTSP-only swap; dropped `HttpMjpegVideoSource`; CV runs on real camera.
- plan.md: goals #4, architecture, success criteria, and Open Questions updated accordingly.

### Whole-Plan Consistency Sweep (Step 7)
- No stale `WEBCAM` literal remains in any phase (Phase 2/3/plan.md aligned).
- Architecture diagram, goals, and Phase 3 steps all agree: laptop webcam = display-only;
  real RTSP camera = CV via Phase 10.
- Seed file/line consistent across plan.md and Phase 2 (`database.py:90`).
- Unresolved contradictions: none. Plan is eligible for implementation.
