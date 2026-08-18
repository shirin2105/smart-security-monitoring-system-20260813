# Phase 10 final delivery report

Date: 2026-08-15. Scope: RTSP/CCTV input pipeline only. Status: **MERGE-READY WITH DOCUMENTED HARDWARE LIMITATION**.

## Delivery status

| Area | Evidence | Status |
|---|---|---|
| Source/factory | `app/sources/factory.py`, `app/sources/rtsp_source.py` | COMPLETE |
| Worker continuity | `app/cv/worker.py`, live frame timing/sampling, reset hooks | COMPLETE |
| Health/isolation | `camera_health.py`, multi-camera runner, disabled config example | COMPLETE |
| Automated validation | 103/103 tests + 8 subtests; focused E/F/I lint clean | PASS |
| Phase 9 regression | Unified worker, Phase7C, MP4 timestamps, CVEvent validation in automated suite | PASS |
| ABODA final rerun | 320 frames/calls; 2 persisted valid events; no duplicate lifecycle records | PASS |
| RTSP hardware | No accessible real camera/stream in validation environment | **NOT HARDWARE VERIFIED** |
| Review | Independent re-review confirms all three production blockers cleared | PASS |

## Files and architecture

- New source boundary: `create_video_source(camera_config)` routes file types to `MP4VideoSource`; `RTSP|CAMERA|LIVE` to `RTSPVideoSource`.
- Runtime path unchanged after input: `source -> DEIMv2 -> ByteTrack -> shared camera TrackStore -> intrusion/crowd/Phase7C adapters -> CVEventManager -> CVEvent v1 -> publisher`.
- A capture thread continuously drains RTSP into one replaceable latest-frame slot. Overwritten frames are counted, preventing native/application backlog while inference is slower than capture.
- Multi-camera runner passes camera-local config, shares a serialized detector wrapper, and contains per-camera failures.

## State, reconnect, continuity

- Source states: `DISCONNECTED -> CONNECTING -> CONNECTED`; failures enter `DEGRADED`, then `RECONNECTING` with interruptible exponential backoff (1s, 2s, 4s...; 15s default cap).
- Frame IDs remain monotonic across reconnect sessions. Accepted wall-clock timestamps clamp backward clock movement.
- Short outage: no fabricated frames; existing temporal state preserved.
- Long outage (`reset_after_s`): active lifecycles publish controlled END first; tracker, TrackStore, adapters, and event manager reset; detector remains loaded. Offline duration cannot become Phase7C dwell/owner-away time.

## Health and credential safety

Health fields: connection state; reconnect count; consecutive/read-decode failures; last reconnect; frames received/processed/dropped-skipped; source/processed FPS; last-frame time/age; inference errors/latency and aggregate status.

Credentials: RTSP passwords redacted; errors identify camera/type without full secret-bearing URI. Example config uses disabled `${RTSP_TEST_URL}` only. No credential committed.

## Failure matrix evidence

Fake capture/source tests cover source mapping, redaction, initial open failure, midstream read failure, reconnect disabled, capped backoff (**1s, 2s, 4s, 4s proof**), external stop during backoff, idempotent release, timestamp/frame-ID monotonicity, invalid live FPS sampling, controlled END-before-reset (**publish precedes tracker/TrackStore/adapter reset proof**), temporal reset without detector replacement, health metrics, and healthy-peer completion after camera failure.

## Limitations and merge gate

- OpenCV open/read timeout properties are backend/build dependent. Retry waits are interruptible; implementation cannot forcibly guarantee interruption of a native `VideoCapture.read()` blocked inside every OpenCV backend.
- No real RTSP hardware 5-10 minute run or disruption/recovery test. Status stays **NOT HARDWARE VERIFIED**, which the bundle permits with the manual guide.
- Fresh ABODA production regression passed and wrote `artifacts/phase10-aboda-final/aboda.jsonl`.
- Open/read timeout values are passed as FFmpeg `VideoCapture.open` parameters; unsupported backends still fall back to their native behavior.

The Phase 10 bundle is merge-ready. Hardware verification remains an explicit operational follow-up rather than a claimed PASS.

## Next actions

1. Hardware owner — optionally run `docs/phase10/RTSP_MANUAL_TEST.md` when target equipment is available.
2. Maintainer — review and commit the focused Phase 10 changes.

## Unresolved questions

- None for bundle completion; hardware ownership remains an operational scheduling question.
