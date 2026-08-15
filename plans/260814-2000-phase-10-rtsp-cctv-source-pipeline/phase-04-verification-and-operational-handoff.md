---
phase: 4
title: "Verification and operational handoff"
status: completed
priority: P1
effort: 2h
dependencies: [1, 2, 3]
---

# Phase 04: Verification and operational handoff

Progress: automated gates complete (**103/103 tests + 8 subtests**); focused E/F/I lint clean. Fresh ABODA production regression passed. Hardware remains explicitly **NOT HARDWARE VERIFIED**, which is accepted by the bundle when no camera is available. Independent re-review confirms all production blockers cleared.

## Overview

Prove fake failure behavior, preserve Phase 9, then record real-hardware result accurately.

## Related Code Files

- Create/modify: `tests/unit/test_rtsp_source.py`, `tests/integration/test_rtsp_worker_continuity.py`, `docs/phase10/RTSP_MANUAL_TEST.md`, Phase 10 report.
- Regression references: `tests/integration/test_unified_cv_worker.py:8-59`, `tests/unit/test_video_timestamps.py:5-26`.

## Implementation Steps

1. Execute the bundle matrix RTSP-01 through RTSP-12 with injected fake captures/source clock.
2. Run focused CV regression, MP4 regression, CVEvent v1 validation, and known ABODA real-video regression.
3. If an accessible RTSP stream exists, use it per manual guide. Otherwise explicitly mark `NOT HARDWARE VERIFIED`.
4. Review credential scan and publish final evidence: state machine, reset semantics, test output, limitations, merge gate.

## Success Criteria

- [x] Fake-source failure matrix passes: factory selection, redaction, open/read failure, reconnect/backoff cap, stop interruption, idempotent release, monotonic frames/timestamps, continuity/reset, health, and peer isolation.
- [x] Phase 9 unified/Phase7C/MP4/CVEvent automated regressions pass within the 103-test suite plus 8 subtests; focused E/F/I lint clean.
- [x] Fresh ABODA regression passes: 320 frames, 320 detector calls, 2 persisted schema-valid `ABANDONED_OBJECT` records, no duplicates.
- [x] Real RTSP status is recorded as **NOT HARDWARE VERIFIED**, with a runnable manual guide, as permitted by the bundle gate.
- [x] Manual guide is runnable without credentials in source control.
- [x] Independent re-review confirms long-outage timing, latest-frame freshness, and open-time timeout parameters are correct; no blocker remains.

## Merge Gate

**MERGE-READY WITH DOCUMENTED HARDWARE LIMITATION.** Automated gates and fresh ABODA regression are green. The bundle accepts `NOT HARDWARE VERIFIED` plus a manual guide when no camera is available. OpenCV timeout properties remain backend-dependent.

## Unresolved Questions

- Who owns the optional target-camera manual run and evidence capture?

## Rollback

Revert Phase 10 commits. Existing MP4 config and canonical JSONL publisher require no migration.
