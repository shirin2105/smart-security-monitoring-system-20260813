---
phase: 3
title: "Phase 3: Real RTSP camera swap and CV detection"
status: completed
priority: P2
effort: "3h"
dependencies: [1, 2, 260814-2000-phase-10-rtsp-cctv-source-pipeline]
---

<!-- Updated: Validation Session 1 - laptop webcam is display-only; CV deferred to the real RTSP camera. Drop HttpMjpegVideoSource for now. -->

# Phase 3: Real RTSP camera swap and CV detection

## Overview

Later step. Swap camera #3 from the laptop webcam to a **real RTSP camera** by reusing
Phase 10's `RTSPVideoSource` + `create_video_source` (no worker changes). CV detection
then runs on the real camera automatically through the existing Phase 10 path. The laptop
webcam remains display-only (decided in validation: no CV on the webcam now).

## Requirements

- Functional:
  - Setting `source_type: RTSP` + `source_uri: ${CAMERA_3_URL}` on camera #3 switches it to
    the real camera in the worker and (via `stream_url`) on the web tile.
  - The unified `CVWorker` processes it via the existing `RTSPVideoSource` path — no new
    detector/tracker/adapter code.
- Non-functional:
  - Zero new source classes needed; the RTSP path already exists from Phase 10.

## Architecture

```
real RTSP camera ──RTSPVideoSource (Phase 10)──► CVWorker (unchanged) ──► CVEvent v1
web tile stream_url ──► MJPEG gateway or direct RTSP preview (TBD at swap time)
```

- `RTSPVideoSource` already exists (`app/sources/rtsp_source.py`) and is selected by
  `create_video_source` for `source_type in {"RTSP","CAMERA","LIVE"}`
  (`app/sources/factory.py:19`). The real camera is a pure config swap.
- For the web preview of an RTSP camera, reuse the Phase 1 MJPEG server generalized to pull
  an RTSP URL, or adopt an RTSP→HLS gateway; decide at swap time (out of scope for the
  laptop-webcam phase).

## Related Code Files

- Modify: `configs/cameras.yaml` — add/adjust camera #3 with `source_type: RTSP`,
  `source_uri: ${CAMERA_3_URL}`, `rtsp:`/`reconnect:` blocks (copy from the existing
  `rtsp_test_01` entry at `configs/cameras.yaml:18-32`).
- Modify (backend seed, when used by web): `back-end/app/db/database.py:90` —
  `stream_url` points at the RTSP preview endpoint, `source="CV"`.

## Implementation Steps

1. Add camera #3 RTSP config to `cameras.yaml` (disabled by default; enable when the real
   camera URL is provided via env). Copy the `rtsp:`/`reconnect:`/`continuity:` blocks from
   `rtsp_test_01`.
2. Verify `CVWorker` picks `RTSPVideoSource` for it (no code change expected).
3. Decide and wire the web preview source (MJPEG gateway vs HLS) for the RTSP camera.
4. Run the worker on the live RTSP feed; confirm `cv-events.jsonl` receives real events and
   the web tile shows the camera.

## Success Criteria

- [x] Camera #3 switches to the real RTSP camera via config only (no worker code change).
- [x] CV detection runs on the real camera through the Phase 10 pipeline.
- [x] `RTSPVideoSource` reconnect/timeout behavior from Phase 10 still holds for camera #3.
- [x] No `HttpMjpegVideoSource` needed for the laptop webcam (display-only).

## Risk Assessment

- **GPU on laptop**: DEIMv2 CPU inference may be <1 fps; if enabling CV on the webcam now,
  set low `inference_fps` and document expected latency. Prefer deferring real CV to the
  RTSP camera (which may have a GPU host).
- **Device double-open**: strictly enforced by single-owner rule (Phase 1 server owns the
  device; worker reads HTTP).
- **RTSP auth in logs**: reuse `redact_rtsp_uri` when logging the camera #3 URI.
