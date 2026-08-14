---
title: "Phase 9.1 repo cleanup and runtime truth alignment"
description: "Remove only proven-dead CV legacy paths and make current documentation/configuration match the validated Phase 9 runtime."
status: pending
priority: P1
effort: 14h
branch: develop
tags: [computer-vision, cleanup, migration, documentation]
blockedBy: []
blocks: []
created: 2026-08-14
---

# Phase 9.1 repo cleanup and runtime truth alignment

## Overview

Scope is cleanup and runtime-truth alignment after completed Phase 9. The runtime contract stays unchanged: DEIMv2 → ByteTrack → one camera-local TrackStore → intrusion/crowd/Phase7C adapters → CVEventManager → validated `cv-event-v1` → `JsonlPublisher`. No Phase 10, RTSP, backend, LLM, database, frontend, model retraining, tracker replacement, or broad refactor.

## Evidence and constraints

- `app/cv/worker.py:64-84` constructs the current detector, tracker, store, three adapters, manager, and JSONL publisher; it rejects legacy keys at `:71-74`.
- `configs/event_rules.yaml:12-49` already carries the live Phase7C threshold tree. Preserve values; do not invent abbreviated keys.
- `README.md:111-136`, `docs/system-architecture.md:3-18`, and `reports/phase9-real-video-regression.md:1-41` record the validated runtime and regression evidence.
- Worktree is dirty and contains untracked datasets/artifacts. Baseline captures state only; no cleanup command may delete, move, stage, or rewrite unowned files.
- Existing in-progress plans for Phase 8 validation and CV/LLM web integration overlap only in historical/legacy material. This plan must not edit their files or alter their contracts.

## Phases

| # | Phase | Depends on | Status |
|---|---|---|---|
| 1 | [Freeze and classify references](./phase-01-freeze-and-classify-references.md) | none | Pending |
| 2 | [Align active configuration and documentation](./phase-02-align-active-config-and-documentation.md) | 1 | Pending |
| 3 | [Remove proven-dead legacy CV surface](./phase-03-remove-proven-dead-legacy-cv-surface.md) | 1, 2 | Pending |
| 4 | [Regression, evidence, and merge gate](./phase-04-regression-evidence-and-merge-gate.md) | 2, 3 | Pending |

## Success Criteria

- [ ] Active config stays Phase7C-only and is loadable; its thresholds are byte-for-byte unchanged unless an audit proves a stale key.
- [ ] Current docs identify DEIMv2, ByteTrack, shared TrackStore, Phase7C, CVEvent v1, and JsonlPublisher; remaining historical mentions are clearly `LEGACY`.
- [ ] `app.vlm`, `StaticRegionDetector`, old static abandoned engine, and dependent demo/tests are deleted only after the audit proves no active import/call/config edge; otherwise they remain explicitly legacy and isolated.
- [ ] Focused contract/worker/adapter/publisher/config tests and the known ABODA smoke pass; webcam is PASS only after human hardware verification, otherwise `NOT HARDWARE VERIFIED`.
- [ ] Final grep classification has zero active-runtime/current-doc hits for static-region/VLM/YOLO/StrongSORT claims; Phase 10 work remains absent.

## Dependency and rollback rule

Phases 2 and 3 may run in parallel only after Phase 1 locks an exclusive file inventory; no file may have two owners. Each implementation commit is reversible independently. Restore a deletion by reverting its commit, then restore the matching tests/demo in the same revert; do not re-enable removed config keys. No persisted schema or event migration exists.

## Open questions

None. Hardware webcam verification remains a manual, non-blocking evidence state.
