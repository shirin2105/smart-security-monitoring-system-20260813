---
phase: 4
title: "Phase 4: Run guide and verification"
status: completed
priority: P2
effort: "1h"
dependencies: [1, 2, 3]
---

# Phase 4: Run guide and verification

## Overview

Document how to start the webcam stream server and verify camera #3 shows a live feed,
covering both mock and real-backend modes, plus a manual hardware checklist (the existing
Phase 10 plan is truthfully "NOT HARDWARE VERIFIED" — this plan inherits that honesty).

## Requirements

- Functional:
  - A single documented command to start the webcam server.
  - A verification checklist: live motion visible, badge is live, offline state on stop,
     no device double-open.
- Non-functional:
  - Docs live in `docs/` per the project documentation standard.

## Related Code Files

- Create/Modify: `docs/camera-3-live-webcam.md` (or extend `README.md` demo section).
- Reference: `reports/phase9-real-video-regression.md`, `reports/phase10b-final-report.md`.

## Implementation Steps

1. Write run steps: `python -m app.webcam_stream_server --index 0 --port 8081 --camera-id 3`,
   then start backend + frontend, open the camera grid.
2. Document the camera-permission step (OS camera access prompt).
3. Add a verification matrix: tile shows motion; stopping server → OFFLINE; `curl` MJPEG
   returns `multipart/x-mixed-replace`; only one `VideoCapture` handle exists (check via
   OS process/device handle).
4. Add the RTSP swap snippet for the later real camera.

## Success Criteria

- [x] A new operator can start the live feed on camera #3 from the docs alone.
- [x] Verification matrix is filled in honestly (hardware-verified or marked pending).
- [x] No secrets (camera URLs with credentials) are written into docs; use `${...}` env refs.

## Risk Assessment

- **Hardware not verified in CI**: mirror Phase 10's manual-guide approach; mark runtime
  verification as operator-performed, not CI-gated.
