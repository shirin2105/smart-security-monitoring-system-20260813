---
title: "Phase 9 Unified CV Event Engine"
description: "Migrate production CV to one DEIMv2/ByteTrack/TrackStore flow emitting three lifecycle-managed CVEvent v1 types, then remove legacy VLM/static-region paths after regression passes."
status: completed
priority: P1
effort: 8d
branch: develop
tags: [feature, computer-vision, refactor, critical]
blockedBy: []
blocks: []
created: 2026-08-14
---

# Phase 9 Unified CV Event Engine

## Overview

Accepted authority: bundle `PHASE9_AGENT_PLAN.md`, `CHECKLIST.md`, `MIGRATION_MAP.json`. Scope only CV runtime. No Phase10, backend, frontend, LLM, retraining, S4, EdgeCrafter, Re-ID, or RTSP optimization.

## Current Evidence

- Final CV report: `../../reports/phase9-final-report.md`.
- Real-video regression: **4/4 PASS** — ABODA abandoned, Walk1 intrusion, Meet_Crowd crowd, Browse1 negative; detector calls equal processed frames; no exact duplicate payload or invalid lifecycle.
- Required Phase 9 CV tests: **78 passed + 8 subtests**. Webcam devtool: **3/3 passed**.
- Webcam code READY; physical hardware validation remains USER MANUAL. No automated hardware PASS claimed.
- `CVEventPublisher.publish(CVEvent)` is the final CV boundary. `JsonlPublisher` is canonical; backend endpoint NOT REQUIRED.
- Active production VLM/static-region and stale YOLO/Ultralytics/StrongSORT routes removed; retained material legacy-classified.

## Phases

| # | Phase | Depends on | Status |
|---|---|---|---|
| 1 | [Freeze baseline and contract](./phase-01-freeze-baseline-and-contract.md) | Phase 8 evidence | Completed |
| 2 | [Unify engines and lifecycle](./phase-02-unify-engines-and-lifecycle.md) | 1 | Completed |
| 3 | [Migrate production worker and config](./phase-03-migrate-production-worker-and-config.md) | 2 | Completed |
| 4 | [Regression, video, webcam gates](./phase-04-regression-video-and-webcam-gates.md) | 3 | Completed: webcam hardware USER MANUAL |
| 5 | [Remove legacy runtime and update docs](./phase-05-remove-legacy-runtime-and-update-docs.md) | 4 PASS | Completed |

Implementation progress: **5/5 phases complete (100%)**. CV merge readiness: **READY**.

## Mandatory Order Mapping

`baseline/tests → contract → one inference → shared tracking/store → intrusion → crowd → Phase7C abandoned → worker switch → event manager → unit/integration/regression → video → webcam → VLM cleanup → YOLO cleanup → docs`. Phase 5 is forbidden until Phase 4 regression passes; webcam may be `NOT HARDWARE VERIFIED`, never fabricated PASS.

## Data Flow

`FrameData → DEIMv2.detect once → person/luggage detections → shared ByteTrack → shared TrackStore snapshot → intrusion/crowd/Phase7C adapters → lifecycle signals → CVEventManager(active registry, stable ID, dedup) → validated CVEvent v1 → existing publisher/JSONL hook`.

## Backward Compatibility / Rollback

- Preserve detector weights, thresholds, publisher seam, `CVWorker.run()` call sites, and cv-event-v1 schema. Add Phase7C config before switching worker; legacy config remains readable but ignored with warning until cleanup.
- Roll back Phases 1-3 by reverting their exclusive files/config together; no persisted data migration. Phase 5 deletion is a separate commit, reverted independently to restore old runtime.

## Success Criteria

- [x] Exactly one detector call per processed frame; one camera-local shared tracker/store snapshot consumed by all engines.
- [x] Only `ZONE_INTRUSION`, `CROWD_THRESHOLD`, `ABANDONED_OBJECT`; all schema-valid CVEvent v1 with stable START/UPDATE/END ID and dedup.
- [x] Phase7C known-positive, false-person filter, and physical stitching regressions pass through production path.
- [x] Video passes; webcam limitation recorded as USER MANUAL; source/camera release covered.
- [x] After regression: zero active production `app.vlm`, static-region abandoned, YOLO/Ultralytics/StrongSORT route; retained material legacy-classified.

## Unresolved Questions

None for Phase 9 CV merge readiness. Webcam hardware verification remains user manual.
