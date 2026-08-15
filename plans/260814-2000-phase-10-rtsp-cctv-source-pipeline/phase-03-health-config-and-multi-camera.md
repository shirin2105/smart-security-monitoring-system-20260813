---
phase: 3
title: "Health, configuration, and camera isolation"
status: completed
priority: P2
effort: 3h
dependencies: [1, 2]
---

# Phase 03: Health, configuration, and camera isolation

Progress: complete. In-process health exposes source/reconnect/frame metrics; disabled credential-free RTSP example and camera failure isolation verified.

## Overview

Extend the existing health monitor with source metrics and provide safe disabled RTSP configuration.

## Related Code Files

- Modify: `app/sources/camera_health.py:6-39`, `configs/cameras.yaml:1-16`, `app/cv/multi_camera_runner.py:35-49`.
- Create: `docs/phase10/RTSP_MANUAL_TEST.md`; tests for health/isolation.

## Implementation Steps

1. Reuse `CameraHealthMonitor`; add connection state, reconnect count, consecutive read failures, last reconnect, received/processed/dropped frames, source/processed FPS and frame age.
2. Add disabled `${RTSP_TEST_URL}` example only; do not modify simulated regression camera entries or commit a secret.
3. Assert camera-local source state/health and that a flapping worker cannot terminate a healthy `MultiCameraRunner` peer.

## Success Criteria

- [x] `get_status()` reports connection state, reconnect/read-failure counters, reconnect time, received/processed/dropped-skipped frames, source/processed FPS, frame age, and inference latency without URI credentials.
- [x] Healthy camera completes when a peer fails.
- [x] Existing MP4 cameras/config load unchanged; RTSP example remains disabled and credential-free.

## Risk Assessment

Do not expose a backend health endpoint: status remains in-process, avoiding backend scope expansion.
