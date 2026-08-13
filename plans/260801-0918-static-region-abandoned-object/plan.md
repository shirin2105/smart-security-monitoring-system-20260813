---
title: "Static-region abandoned-object detection"
description: "Replace luggage-class candidate generation with fixed-camera background analysis, deterministic timing, optional VLM validation, and a real-video demo."
status: completed
priority: P1
effort: 14h
branch: master
tags: [computer-vision, abandoned-object, vlm, demo]
created: 2026-08-01
---

# Static-region abandoned-object detection

## Outcome

Detect newly introduced persistent foreground regions on fixed cameras without requiring YOLO luggage classes. Retain YOLO person detection for proximity context, preserve `EventCandidate`, optionally validate matured regions through a local/Hugging Face VLM adapter, and generate a reproducible annotated demo from `tests/clips/pets2006_3.mp4`.

## Scope

- In: background warm-up, foreground cleanup, region persistence/clearing, person context, deterministic video timestamps, optional fail-open VLM validation, real-video demo.
- Out: moving-camera compensation, model training, generic object classification, API/schema breaking changes, rewriting legacy experiment scripts.

## Phases

| Phase | Work | Status | Depends on |
|---|---|---|---|
| [01](phase-01-deterministic-video-time-and-contracts.md) | Stable time and contracts | completed | none |
| [02](phase-02-static-region-detector.md) | Background/static-region detector | completed | 01 |
| [03](phase-03-event-engine-and-worker-integration.md) | Event and worker integration | completed | 01, 02 |
| [04](phase-04-vlm-validation-and-real-video-demo.md) | Optional VLM and real-data demo | completed | 03 |

## Dependency and ownership graph

`01 contracts/time -> 02 regions -> 03 events/worker -> 04 VLM/demo`

Each file belongs to one phase; no parallel write overlap. Sequential delivery is intentional because later phases consume frozen contracts.

## End-to-end data flow

Video frame + source FPS -> deterministic `captured_at` -> person-only YOLO detections/tracks + raw frame -> background model -> cleaned foreground contours -> stable region IDs/timers -> person-distance context -> optional VLM verdict -> unchanged `EventCandidate` + evidence -> publisher; demo runner also emits annotated MP4 and JSON summary.

## Compatibility and migration

- Keep `AbandonedObjectEngine.evaluate(tracks, frame_data)` and `EventCandidate` fields stable.
- Default VLM mode `disabled`; no token or network required. Existing configs gain defaults.
- Change detector target classes to person only after static-region integration passes. Other event engines continue consuming person tracks.
- Legacy luggage-based scripts remain runnable until the new demo is accepted, then are deprecated in docs—not deleted in this plan.

## Plan-level test matrix

| Level | Coverage |
|---|---|
| Unit | frame/FPS timestamps; masks/morphology/region matching; warm-up; persistence; clearing; VLM parsing/fallback |
| Integration | worker preserves intrusion/crowd; abandoned event from unlabeled static region; no event for baseline/moving person/camera noise |
| E2E/demo | same clip/config produces same alert frame/time; MP4 opens; JSON event/evidence exists; offline mode works |

## Rollback

Revert phases in reverse order. Config defaults and preserved public contracts prevent cascading data migration. Before phase 03 cutover, retain the prior engine behind `candidate_source: tracked_classes`; one config switch restores prior behavior.

## Measurable success

- An unlabeled introduced object held for configured duration produces exactly one abandoned candidate.
- A baseline object, transient foreground, and person motion do not produce candidates in fixtures.
- Reprocessing identical video yields identical alert frame ID and timestamps.
- `tests/clips/pets2006_3.mp4` produces playable annotated MP4 plus machine-readable event summary without injected detections.
- Full pytest suite passes; no secret required; VLM outage does not stop CV processing.

## Validation log

- Tier: Standard (4 phases). Claims checked against live code on 2026-08-01.
- Verified: current engine filters luggage classes (`app/events/abandoned_object.py:156,181-183`); worker routes one shared track list to three engines (`app/cv/worker.py:84-100`); MP4 timestamps currently use wall clock (`app/sources/mp4_source.py:31-47`); existing demo injects a backpack detection (`scripts/process_real_abandoned_with_drop.py:98-108`).
- Verified: 35 relevant tests passed; final review spec PASS; PETS summary records 1,510 frames, 30 FPS, deterministic media timestamps, three events, untouched source, and generated MP4.
- Validation limitations: live Hugging Face call not executed; six-camera supervisor verified with fakes, not a real-load benchmark.
- Scope change: canonical real demo changed from `vtest.avi` to PETS 2006 because PETS visibly contains the unattended bag. User required real data and did not select `vtest.avi`; no delivery impact.

## Unresolved questions

None blocking. Fixed-camera and fail-open VLM assumptions retained; PETS 2006 is canonical real demo clip.
