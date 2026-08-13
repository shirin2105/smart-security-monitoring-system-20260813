---
title: "DEIMv2 Phase 7A production runtime replacement"
description: "Replace the accidental YOLO detector and simple IoU tracker with the verified DEIMv2 Phase 7A and class-wise ByteTrack runtime while preserving ingest, backend, and frontend contracts."
status: completed
priority: P1
effort: 12h
branch: codex/feat/deimv2-runtime
tags: [refactor, computer-vision, deimv2, bytetrack, critical]
blockedBy: []
blocks: []
created: 2026-08-11
---

# DEIMv2 Phase 7A production runtime replacement

## Outcome

Production frames use the frozen Phase 7A checkpoint and class-isolated ByteTrack. Existing source, event-engine, publisher, backend ingest, and frontend behavior remain unchanged.

## Scope

- In: detector/tracker adapters, model configuration, runtime dependencies, startup validation, unit/integration tests, deployment notes.
- Out: retraining, Phase 7C/8 logic changes, event schema changes, API/UI work, throughput redesign, full external E2E deployment.
- Reuse: `devtools/webcam_cv_test/model_runtime.py` behavior and parent `model-CV-v1` Phase 7A/7B.1 assets; port stable logic into production-owned modules rather than importing devtool/Kaggle scripts at runtime.

## Data Flow

`MP4VideoSource -> FrameSampler -> DEIMv2Detector -> list[DetectionResult] -> ByteTrackTracker -> list[TrackResult] -> TrackStore -> existing event engines -> existing publisher/ingest/UI`

Only the two middle components change. `FrameData`, `DetectionResult`, `TrackResult`, and `EventCandidate` remain the boundaries.

## Phases

| Phase | Name | Status | Depends on | Effort |
|---|---|---|---|---|
| 1 | [Lock contracts and tests](./phase-01-lock-contracts-and-tests.md) | Complete | None | 3h |
| 2 | [Port DEIMv2 detector and ByteTrack](./phase-02-port-deimv2-detector-and-bytetrack.md) | Complete | Phase 1 | 6h |
| 3 | [Integrate, configure, and validate](./phase-03-integrate-configure-and-validate.md) | Complete | Phase 2 | 3h |

## Dependency / Ownership Rules

- Sequential execution required; tests define contracts before runtime changes.
- Exclusive ownership is recorded per phase. No parallel phase edits the same file.
- Parent-workspace assets are evidence/source inputs, not runtime-relative paths. Required assets must be copied/provisioned into documented production locations.

## Compatibility and Rollback

- No public JSON, database, REST, WebSocket, or UI contract changes.
- Keep detector/tracker injection seams so tests and emergency rollback remain possible.
- Rollback is one revert of phases 2-3 plus restoration of prior dependency/config files; no data migration required.

## Global Success Criteria

- No production import/reference to Ultralytics or YOLO.
- Missing/incompatible model assets fail startup explicitly; never emit silent empty detections.
- Deterministic tests prove class mapping, box/score conversion, class-isolated IDs, empty-frame aging, worker call flow, and unchanged event publishing.
- Existing backend/frontend and unrelated CV tests remain green.

## Final review blocker closure

- Production artifact identity is mandatory before unsafe checkpoint deserialization; shipped checkpoint/backbone hashes are pinned.
- Worker startup failures execute source and event-engine cleanup.
- Shared detector serialization has a real concurrent max-in-flight regression test.
- ByteTrack first-seen state expires after the configured lost-track continuity window.
- Docker relies on the scoped DEIMv2 importer; `.qa-tmp/` is ignored because policy blocks cleanup.

## Completion Evidence

- Targeted runtime: 25/25 passed; legacy integrations: 6/6 passed.
- Full suite: 205 passed, 4 skipped, 8 subtests passed, 0 failed.
- Real Phase 7A checkpoint CPU smoke passed; pinned checkpoint/backbone hashes matched.
- Final re-review: MERGE. Backend/frontend changes: 0/0.
- Coverage unavailable because compatible tooling absent; non-blocking QA follow-up.

## Unresolved Questions

- None.
