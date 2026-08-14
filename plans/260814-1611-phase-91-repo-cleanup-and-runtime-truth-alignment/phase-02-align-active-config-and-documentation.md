---
phase: 2
title: "Align active configuration and documentation"
status: pending
priority: P1
effort: "4h"
dependencies: [1]
---

# Phase 2: Align active configuration and documentation

## Overview

Make active configuration and current architecture documentation say exactly what the unified Phase 9 runtime executes, while preserving validated thresholds and historical evidence.

## Architecture and data flow

`Settings.event_rules` loads `configs/event_rules.yaml` (`app/config.py:48-49`) → `CVWorker` reads abandoned rules (`app/cv/worker.py:68-77`) → validates the nested Phase7C object (`:185-212`) → passes it to `Phase7CAbandonedAdapter` (`:78-81`) → the adapter constructs its production core config (`app/cv/events/phase7c_abandoned_adapter.py:27-50`). Documentation must match this flow and the publisher boundary at `app/publisher/base.py:13-16`, `app/publisher/jsonl_publisher.py:9-20`.

## Related files and ownership

- Modify (exclusive): `configs/event_rules.yaml`, `README.md`, `docs/system-architecture.md`.
- Create (exclusive): `docs/architecture/current_cv_runtime.md`, `docs/phase9/WEBCAM_MANUAL_CHECKLIST.md` (only if absent; otherwise modify it).
- Read: `app/cv/worker.py:64-84,185-212`, `app/cv/events/phase7c_abandoned_adapter.py:27-50`, `reports/phase9-real-video-regression.md:1-41`.
- Must not modify: `app/cv/worker.py`, event schema, backend, LLM, frontend, Phase 10 files.

## Implementation steps

1. Use Phase 1 audit to remove only keys classified `ACTIVE_CONFIG`-stale. Current baseline already exposes only `abandoned_object.phase7c` at `configs/event_rules.yaml:12-49`; preserve all threshold values and nesting unless traced code shows an unused stale key.
2. Add/configure no `candidate_source`, `static_region`, `vlm`, VLM provider/model, or alternative abandoned engine key. Worker rejection is intentional compatibility protection (`app/cv/worker.py:71-74`), not a reason to reintroduce deprecated config.
3. Update current-stack sections in README and system architecture: DEIMv2; normalized person/generic luggage; ByteTrack; shared TrackStore; `ZONE_INTRUSION`, `CROWD_THRESHOLD`, `ABANDONED_OBJECT`; Phase7C temporal reasoning; `CVEvent v1`; `CVEventPublisher`/`JsonlPublisher` JSONL boundary. Preserve `EventCandidate` text only where labelled backend compatibility/legacy, per `README.md:136`.
4. Make all remaining VLM/static-region/YOLO/StrongSORT historical material visibly `LEGACY`; do not delete evidence reports. Put the compact canonical diagram and non-goals in `docs/architecture/current_cv_runtime.md`.
5. Create/update a manual webcam checklist: prerequisites, no credentials, intrusion right-half, crowd with two persons, Phase7C abandoned scenario, JSONL inspection, clean camera release, and result vocabulary `PASS` or `NOT HARDWARE VERIFIED` only.

## Test matrix

| Level | Check | Expected observable result |
|---|---|---|
| Unit | `tests/unit/test_cv_worker_publisher_config.py` | defaults to JSONL; malformed Phase7C config fails before frames. |
| Integration | `tests/integration/test_temporal_worker_eos.py` | worker consumes `hold_s=3.0`, `away_hold_s=5.0`; EOS cleanup remains intact. |
| Static | final config/doc grep | no active config/current-doc stale claims; historical hits labelled `LEGACY`. |

## Risks and mitigation

| Risk | Likelihood × impact | Mitigation / rollback |
|---|---|---|
| Documentation changes corrupt README mixed Vietnamese/English content | Low × Medium | Limit edits to CV sections; review diff with UTF-8; revert the docs-only commit. |
| Threshold “cleanup” changes observed Phase7C behavior | Medium × High | No semantic threshold edits; compare YAML subtree before/after and run Phase 4 regression. |
| Compatibility wording falsely implies backend change | Medium × Medium | Keep scope boundary explicit; do not edit `EventCandidate` classes/routes. |

## Success criteria

- [ ] Config load succeeds and Phase7C baseline values remain unchanged.
- [ ] Current docs contain exactly one canonical current-runtime explanation and correctly label legacy material.
- [ ] Webcam checklist never fabricates hardware success.

## Rollback

Revert the configuration/docs commit as one unit. It changes no persisted data or runtime schema.

## Next steps

Provides current truth to Phase 3 and the validation statements for Phase 4.

