---
phase: 2
title: "Worker continuity and live sampling"
status: completed
priority: P1
effort: 6h
dependencies: [1]
---

# Phase 02: Worker continuity and live sampling

Progress: complete. Worker uses source factory/config, timestamp sampling for live input, controlled END-before-reset, camera-local temporal reset, and detector continuity.

## Overview

Wire the factory into the worker and make temporal state safe across RTSP outages without modifying detector or event algorithms.

## Related Code Files

- Modify: `app/cv/worker.py:24-190`, `app/cv/frame_sampler.py:4-13`, `app/cv/multi_camera_runner.py:25-49`.
- Create/modify: focused source/worker integration tests.

## Implementation Steps

1. Add injectable source or source factory to `CVWorker`; retain constructor compatibility and pass `camera_config` from `MultiCameraRunner`.
2. Separate per-camera runtime construction from detector construction. On long outage: publish `end_all()` while old manager is valid, then instantiate a fresh tracker, TrackStore, adapters, and manager; do not call detector factory.
3. Make event clocks live-time based for RTSP. Current adapters derive `now_s` from frame/FPS (`intrusion_adapter.py:10-12`, `crowd_adapter.py:10-12`, `phase7c_abandoned_adapter.py:18-20`), so introduce a shared frame temporal value that uses monotonic elapsed capture time for live sources and retains media semantics for MP4.
4. Implement deadline/timestamp sampling for live frames; retain current frame-ID sampling for file sources.
5. Add tests RTSP-06..10 and lifecycle proof: no active event survives long outage; offline time cannot trigger abandoned immediately; timestamps never regress.

## Success Criteria

- [x] One detector instance remains alive over reconnect/reset.
- [x] Long outage produces controlled END before state replacement.
- [x] Short outage has no fabricated frames/events; long outage resets tracker, TrackStore, adapters, and manager for a new logical session.

## Risk Assessment

Changing the adapter clock has high regression risk. Isolate it in a shared helper with explicit MP4/live branches and run all Phase 9 contract/regression tests.
