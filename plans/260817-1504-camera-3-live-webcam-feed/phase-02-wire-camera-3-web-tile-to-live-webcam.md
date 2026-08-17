---
phase: 2
title: "Phase 2: Wire camera 3 web tile to live webcam"
status: completed
priority: P1
effort: "3h"
dependencies: [1]
---

# Phase 2: Wire camera 3 web tile to live webcam

## Overview

Point camera #3's `previewUrl`/`stream_url` at the MJPEG endpoint from Phase 1 and mark
its source as live, so `CameraGrid` renders it as a live `<img>` feed with a live badge.
Covers both frontend **mock mode** and the **real backend** DB.

## Requirements

- Functional:
  - Camera #3 `stream_url` = `http://localhost:8081/cameras/3/stream` (absolute → kept as-is by `toCamera`).
  - `source`/`sourceType` resolved to a live value so `SourceBadge` no longer shows `Nguồn giả lập`.
  - If the stream server is down, tile degrades to OFFLINE/"no signal" (already handled by
    grid `offline` branch) rather than showing a stale frame.
- Non-functional:
  - No behavior change for cameras #1, #2, #4–#6.

<!-- Updated: Validation Session 1 - reuse LIVE badge, drop WEBCAM union/badge changes; seed target pinned to database.py:90; add reseed step -->

## Architecture

Frontend path already works for non-video preview URLs:
`CameraGrid.tsx:90` → `previewUrl.match(/\.(mp4|webm|avi)/i)` is false →
`LiveCameraVideo` is bypassed → `<img src={previewUrl}>` renders the MJPEG live.
The `source='CV'` value already maps to `sourceType:'LIVE'` in `adapters.ts:179`, so
`SourceBadge` shows `CV thật` with **no frontend union/badge changes** (decided in
validation: reuse `LIVE` rather than add a separate `WEBCAM` label).

## Related Code Files

- Modify (real backend — primary): `back-end/app/db/database.py:90` (camera #3 seed row).
- Modify (mock mode — secondary): `front-end/src/api/mock/fixtures.ts` camera id `3`.
- Reference (no change): `front-end/src/api/adapters.ts:179`, `front-end/src/components/common/Badges.tsx:103`.

## Implementation Steps

1. Edit `back-end/app/db/database.py:90` camera #3 row:
   - `stream_url="http://localhost:8081/cameras/3/stream"` (absolute → passed through by `toCamera`).
   - `source="CV"` (→ `SourceBadge` shows `CV thật`).
   - `status="online"` (currently `"warning"` → DEGRADED; flip to HEALTHY).
2. (Mock mode) Edit `front-end/src/api/mock/fixtures.ts` camera #3:
   `previewUrl: 'http://localhost:8081/cameras/3/stream'`, `sourceType: 'LIVE'`.
3. **Apply seed**: the seed only runs when tables are empty, so delete the SQLite DB file
   (the configured `SQLALCHEMY_DATABASE_URL` path) and restart the backend so
   `init_db_and_seed()` re-creates rows with the new camera #3 values.
4. Start the Phase 1 server, run backend + frontend, confirm camera #3 shows live motion
   with the `CV thật` badge and no `Nguồn giả lập` label.

## Success Criteria

- [x] Camera #3 tile displays the live laptop webcam (not the demo image/video).
- [x] Badge reads a live source (`WEBCAM`/`CV thật`), not `Nguồn giả lập`.
- [x] Other camera tiles unchanged.
- [x] Frontend build + existing component tests pass.

## Risk Assessment

- **CORS/origin**: if frontend runs on a different port, ensure Phase 1 server sends
  `Access-Control-Allow-Origin`. Alternatively proxy `/cameras/*` via the dev server /
  nginx to same origin.
- **Absolute URL assumption**: `toCamera` only prepends `API_BASE_URL` when `stream_url`
  is relative; absolute `http://` URLs pass through unchanged — keep it absolute.
- **Mock vs real mismatch**: verify which mode the running app uses before editing; edit
  the correct source to avoid "still shows demo" confusion.
