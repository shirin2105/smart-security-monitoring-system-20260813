---
title: "Phase 10 RTSP/CCTV source pipeline"
description: "Add reliable realtime RTSP ingestion without changing the frozen Phase 9 CV algorithm."
status: completed
priority: P1
effort: 16h
branch: develop
tags: [phase10, rtsp, cctv, cv, reliability]
created: 2026-08-14
---

# Phase 10 plan

Progress: **4/4 phases complete**. Automated gates pass (**103/103 tests + 8 subtests**); focused E/F/I lint clean. Fresh ABODA production regression passes. Hardware remains truthfully **NOT HARDWARE VERIFIED** with a manual guide, an accepted bundle outcome. Independent re-review confirms all production blockers cleared.

## Scope and invariant

Keep the frozen path `DEIMv2 -> ByteTrack -> shared TrackStore -> three adapters -> CVEventManager -> CVEvent v1 -> JsonlPublisher`. Phase 10 only replaces the input boundary with a factory and an RTSP implementation. No backend, LLM, model, ReID, ONNX/TensorRT, tiling, adaptive scheduling, or Phase 10B work.

## Initial verified baseline (resolved by implementation)

- `CVWorker` constructs `MP4VideoSource` directly at `app/cv/worker.py:60`; its run loop already owns detector, tracker, TrackStore, adapters, manager, publisher, and source release (`app/cv/worker.py:99-142`).
- `MP4VideoSource` is file-only and synthesizes missing clips (`app/sources/mp4_source.py:30-67`), so it must not receive RTSP URLs.
- Current `FrameSampler` derives interval from source FPS (`app/cv/frame_sampler.py:10-13`), unsuitable for unknown/live FPS.
- ByteTrack, TrackStore, and adapters have no public reset method (`app/cv/tracker.py:28-89`, `app/cv/track_store.py:37-63`, `app/cv/events/phase7c_abandoned_adapter.py:27-120`); long-outage reset must recreate these per-camera components without recreating the detector.
- `CVEventManager.end_all()` closes active lifecycles but retains its monotonic-clock map (`app/cv/event_manager.py:80-87`), hence long-outage reset needs a fresh manager after controlled END publication.
- Multi-camera already isolates exceptions but omits `camera_config` when constructing workers (`app/cv/multi_camera_runner.py:35-49`); factory selection would otherwise read global config instead of the submitted camera.

## Data flow and state machine

`camera config -> create_video_source -> RTSPVideoSource -> fresh FrameData(captured_at=accepted wall clock, monotonic frame_id/session) -> timestamp sampler -> unchanged worker pipeline -> CVEvent v1`.

Per source: `DISCONNECTED -> CONNECTING -> CONNECTED`; failed open/read yields `DEGRADED -> RECONNECTING`, with interruptible exponential delay. A short outage preserves runtime state but emits no fabricated frames. At `reset_after_s`, worker first emits controlled END events at the last observed timestamp, then replaces tracker/TrackStore/adapters/manager; reconnect begins a new session. Offline duration never appears in Phase7C history/owner-away dwell.

## Dependency graph

1. Source contracts/factory and test fakes block worker integration.
2. Worker reset/seam integration blocks outage and multi-camera tests.
3. Health/metrics/config/docs depend on source semantics.
4. Fake-source test gates precede MP4/Phase 9 regression; hardware RTSP is manual-only.

## Phases

| Phase | Status | Deliverable | Depends on |
|---|---|---|---|
| [01](phase-01-source-contract-and-rtsp.md) | completed | Factory, RTSP source, redaction, bounded reconnect | none |
| [02](phase-02-worker-continuity-and-live-sampling.md) | completed | Worker integration, live sampling, controlled reset | 01 |
| [03](phase-03-health-config-and-multi-camera.md) | completed | Health metrics, example config, isolation | 01, 02 |
| [04](phase-04-verification-and-operational-handoff.md) | completed | Failure matrix, automated regressions, fresh ABODA proof, and operational handoff | 01-03 |

## Test matrix / measurable acceptance

- Unit: factory mapping; URI redaction; initial/open/read failures; capped exponential backoff; stop during backoff; idempotent release; timestamp/frame-id monotonicity; live FPS 0/fluctuation; latest-only/no accumulation.
- Integration: short and long outage, controlled END/reset, no Phase7C offline-dwell accumulation, detector constructed once, two camera isolation, clean shutdown.
- Regression: `tests/integration/test_unified_cv_worker.py`, Phase7C contract/adapter tests, CVEvent validation, MP4 source/timestamps, and one real ABODA run producing valid CVEvent v1.
- Manual: RTSP camera run 5-10 minutes; disruption beyond reset threshold; recovery without detector reload; no false abandoned event. If unavailable report `NOT HARDWARE VERIFIED`, never PASS.

## Risks, compatibility, rollback

| Risk | Likelihood x impact | Mitigation / rollback |
|---|---|---|
| OpenCV backend ignores timeout properties | M x H | Pass timeout values as FFmpeg open parameters; use bounded retry state and document fallback backend limits. |
| Offline gap corrupts dwell rules | M x H | Do not create frames during gap; long outage controlled END plus new tracker/store/adapters/manager. |
| RTSP password leaks | M x H | Central URI sanitizer for logs/errors/tests; no full URI in repr/log records. |
| Live input overload | M x H | Continuously drain capture into a single-slot latest-frame buffer; count overwritten/skipped frames. |
| MP4 regression | L x H | Factory retains exact MP4 path and existing media timestamp behavior; focused regressions gate merge. |
| One flapping source blocks peers | M x H | Worker-local retry loop, existing per-future failure containment; test camera B completes. |

Backwards compatibility: `SIMULATED`/`FILE`/`MP4` remain `MP4VideoSource`; existing config remains valid; RTSP example stays disabled and credential-free. Roll back by reverting the Phase 10 commit: no schema/database/backend migration and no persisted incompatible state.

## File ownership / parallelism

- Source foundation owner: `app/sources/*`, source tests only.
- Runtime owner: `app/cv/worker.py`, `frame_sampler.py`, `multi_camera_runner.py`, integration tests only.
- Operations owner: `configs/cameras.yaml`, `docs/phase10/*`, health tests only.
Implement sequentially for phases 01 -> 02; phase 03 can start after factory contract stabilizes; phase 04 follows all code.

## Unresolved questions

- Who owns the optional target-hardware run for a 5-10 minute RTSP disruption/recovery proof?
- OpenCV `VideoCapture` timeout support remains backend/build dependent; fake tests prove bounded retry/backoff interruption, not forced interruption of a blocking native read.
