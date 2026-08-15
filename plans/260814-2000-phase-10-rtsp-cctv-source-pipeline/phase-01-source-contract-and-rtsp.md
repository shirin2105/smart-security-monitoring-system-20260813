---
phase: 1
title: "Source contract and RTSP implementation"
status: completed
priority: P1
effort: 5h
dependencies: []
---

# Phase 01: Source contract and RTSP implementation

Progress: complete. Factory mapping, RTSP state/retry loop, monotonic timestamps/frame IDs, redaction, and idempotent release verified by automated tests.

## Overview

Add a source factory and a testable `RTSPVideoSource`; preserve MP4 behavior exactly.

## Related Code Files

- Create: `app/sources/rtsp_source.py`, `app/sources/factory.py`, RTSP source unit tests.
- Modify: `app/sources/base.py`, package exports if present.
- Read-only compatibility reference: `app/sources/mp4_source.py:12-72`.

## Implementation Steps

1. Extend source contract only with optional, backwards-compatible health/session metadata required by the worker; retain `read_frames()`/`release()` at `app/sources/base.py:6-15`.
2. Implement source-type mapping: `SIMULATED|FILE|MP4 -> MP4VideoSource`, `RTSP|CAMERA|LIVE -> RTSPVideoSource`; invalid types fail with redacted configuration context.
3. Implement RTSP open/read/release with injected capture factory, monotonic session/global frame counter, accepted wall-clock `captured_at`, OpenCV timeout property best effort, retry state and interruptible `Event.wait(backoff)`.
4. Sanitize all URI-facing errors/log fields; expose counters without credentials.
5. Add fake capture tests for RTSP-01..05, RTSP-09, RTSP-12.

## Success Criteria

- [x] RTSP URL is never sent to `MP4VideoSource`.
- [x] Retry delay follows exponential policy, caps at configured maximum (15s default), and can stop during backoff.
- [x] `release()` is idempotent; URI-facing behavior redacts passwords.

## Risk Assessment

Native read interruption cannot be guaranteed by every OpenCV build; prove worker-level stop between retries and document backend limitation rather than adding a process architecture outside scope.
