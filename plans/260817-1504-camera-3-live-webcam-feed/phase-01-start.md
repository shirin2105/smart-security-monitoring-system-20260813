---
phase: 1
title: "Phase 1: Webcam MJPEG stream server"
status: completed
priority: P1
effort: "4h"
dependencies: [260814-2000-phase-10-rtsp-cctv-source-pipeline]
---

# Phase 1: Webcam MJPEG stream server

## Overview

Build a small, standalone HTTP server in the `app/` CV package that opens the laptop
webcam via `cv2.VideoCapture(index)`, encodes each frame to JPEG, and streams it as
`multipart/x-mixed-replace` (MJPEG). This is the **single owner** of the webcam device
and the source for camera #3's live `previewUrl`.

## Requirements

- Functional:
  - Capture from a configurable webcam index (default `0`) and optional RTSP/proxy URL later.
  - Serve `GET /cameras/{camera_id}/stream` returning MJPEG.
  - CORS headers so the browser frontend (different origin/port) can load the `<img>`.
  - Graceful start/stop; release the device on shutdown; report device-open failure as HTTP 503.
- Non-functional:
  - Uses the existing `app/` venv (already has `cv2`); no new heavy deps.
  - Bounded frame rate (e.g. 15 fps) to avoid starving the laptop.
  - No unbounded queue; drop frames if a client is slow.

## Architecture

- New module `app/webcam_stream_server.py` (or `app/sources/webcam_stream_server.py`).
- Mirrors the MJPEG pattern already proven in `devtools/webcam_cv_test/app.py:30-39`
  but as a standalone, configurable service (the devtool is demo-only and runs CV too).
- Reuses `live_timestamp_iso`/`redact_*`` helpers from `app/sources/rtsp_source.py` for
  consistent `FrameData`/`source_type` semantics if later fed into the worker.

## Related Code Files

- Create: `app/webcam_stream_server.py`
- Reference (don't modify): `devtools/webcam_cv_test/app.py`, `app/sources/rtsp_source.py`

## Implementation Steps

1. Add `WebcamStreamServer` with `cv2.VideoCapture(index)` open + retry on failure.
2. Encode loop: `ret, frame = cap.read()` → `cv2.imencode('.jpg', frame, [QUALITY])` →
   yield `b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf + b"\r\n"`.
3. Expose `GET /cameras/{camera_id}/stream` (camera_id from path, ignored for single cam
   now but keeps the URL stable for multi-cam later).
4. Add CORS (`Access-Control-Allow-Origin: *`) and `Cache-Control: no-store`.
5. Add `GET /healthz` returning device state (`OPEN`/`NO_DEVICE`).
6. CLI entry: `python -m app.webcam_stream_server --index 0 --port 8081 --camera-id 3`.
7. On `cap.isOpened() == False`, return 503 with JSON `{error:"webcam not available"}`.

## Success Criteria

- [x] `python -m app.webcam_stream_server` opens the laptop webcam and serves MJPEG at
      `http://localhost:8081/cameras/3/stream`.
- [x] Opening that URL in a browser shows live motion.
- [x] `curl -I` shows `Content-Type: multipart/x-mixed-replace; boundary=frame`.
- [x] Killing the process releases the device (no zombie `VideoCapture`).
- [x] Unit-testable: a fake capture factory injected so the encode/yield logic is covered
      without a physical camera (mirror `RTSPVideoSource` `capture_factory` seam).

## Risk Assessment

- **Device contention**: only this server opens the device; CV (Phase 3) reads the HTTP
  stream, never the device directly.
- **No webcam on headless CI**: server must fail cleanly (503), not crash import. Keep the
  import of `cv2` lazy inside the server module so the rest of `app` still imports.
- **Laptop permission**: macOS/Windows may require camera permission; document it.
