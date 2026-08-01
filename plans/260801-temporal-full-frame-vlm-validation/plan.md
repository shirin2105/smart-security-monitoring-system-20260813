---
title: "Temporal full-frame VLM validation"
description: "Validate matured static-region candidates with ordered full-scene frames from eight seconds before through eight seconds after the original candidate time."
status: complete
priority: P1
effort: 11h
branch: master
tags: [feature, backend, computer-vision, vlm]
blockedBy: [260801-0918-static-region-abandoned-object]
blocks: []
created: 2026-08-01
---
# Temporal full-frame VLM validation

## Outcome

Extend the integrated static-region engine so a candidate maturing at event time `T` is validated after `T+8s` using ordered full CCTV frames sampled at 1 FPS over `[T-8s, T+8s]` (maximum 17). If accepted or fail-open, emit the event with `detectedAt=T`, not decision time.

## Scope

- In: bounded full-frame history, pending temporal validation, multi-image Hugging Face request, environment-only token, demo threshold of 6 seconds, compatibility defaults, deterministic tests.
- Out: background jobs/queues, persisted video windows, new public event fields, model training, changes to non-abandoned event engines.

## Cross-Plan Dependency

Builds on the completed static-region detector, engine integration, and HF validator from `../260801-0918-static-region-abandoned-object/plan.md`. No update to that completed plan's status.

## Data Flow

`FrameData(image, captured_at)` -> per-engine bounded full-frame sampler -> static region reaches candidate at `T` -> immutable pending snapshot (`region`, original candidate timestamp, owner/person context) -> collect until `T+8s` -> select ordered samples in `[T-8,T+8]`, default 1 FPS/max 17 -> HF temporal validator -> accepted/unavailable emits candidate timestamped `T`; rejected emits nothing -> publisher receives unchanged `EventCandidate` contract.

## Phases

| Phase | Work | Status | Depends on | Exclusive ownership |
|---|---|---|---|---|
| [01](phase-01-temporal-validation-contract.md) | Contract and HF multi-frame adapter | complete | existing plan | `app/vlm/region_validator.py`, `tests/unit/test_region_validator.py` |
| [02](phase-02-engine-buffer-and-deferred-emission.md) | Buffer, pending state, preserved timestamps | complete | 01 | `app/events/abandoned_object.py`, `tests/unit/test_abandoned_object.py` |
| [03](phase-03-worker-demo-and-integration-validation.md) | Production wiring, demo, integration verification | complete | 02 | `app/cv/worker.py`, `configs/event_rules.yaml`, `scripts/generate_static_abandoned_demo.py`, integration tests |
| [04](phase-04-enable-production-huggingface-temporal-validation.md) | Permanently activate production temporal HF validation | complete | 03 | `configs/event_rules.yaml`, `app/cv/worker.py`, `tests/integration/test_production_vlm_configuration.py` |

## Compatibility and Rollback

- Keep `RegionValidator.validate(crop, region)` implementations usable; add a temporal method/capability with a default single-image bridge. Keep `AbandonedObjectEngine.evaluate(tracks, frame_data)` and `EventCandidate` schema unchanged.
- Existing custom configs may still select disabled/heuristic/crop behavior; shipped production rules now select temporal Hugging Face validation. No schema, persisted-data, API, or token-storage migration.
- Phase 04 rollback changes only the two YAML activation values to `false`/`disabled` and restores the worker fallback; earlier rollback remains phase 03 -> 02 -> 01. No stored-data migration or artifact cleanup because temporal frames remain memory-only.

## Test Matrix

| Level | Observable checks |
|---|---|
| Unit | exact inclusive window/order/count; FPS independence; delayed decision; timestamp preservation; rejection/fail-open; cleanup; HF payload and missing-token no-network |
| Integration | worker routes full frames through production engine; other engines continue; overlapping regions isolated; end-of-stream incomplete window policy |
| E2E/demo | 6-second candidate waits 8 seconds; request has <=17 full frames at ~1 FPS; emitted JSON retains original `T`; source unchanged; secret absent from files/logs/artifacts |

## Plan Risks

- High likelihood/high impact: raw-frame memory growth. Bound by time, sample on ingress, cap 17 frames per camera plus only necessary pending snapshots; clear on decision/region removal/reset.
- Medium likelihood/high impact: synchronous HF call stalls processing at `T+8`. One bounded call per region, strict timeout, cached terminal verdict, existing fail-open behavior; queueing remains out of scope.
- Medium likelihood/high impact: losing `T` while waiting. Store immutable candidate context and build event from it; test `detectedAt`, ID timestamp, `firstSeenAt`, and durations.

## Measurable Success

- HF receives 1-17 chronologically ordered full-scene images covering all available 1-second sample points in `[T-8,T+8]`; no crop-only request in temporal mode.
- No VLM decision occurs before `T+8s`; one decision maximum per region.
- Accepted/unavailable event uses original `T`; rejected event never publishes.
- Full relevant pytest suite passes; repository search finds no HF secret value or persisted raw temporal frame.

## Validation Log

- Standard tier. Verified current synchronous crop validation at `app/events/abandoned_object.py:222-250`; production construction/wiring at `app/cv/worker.py:56-80,85-121`; one-image HF contract/payload at `app/vlm/region_validator.py:17-18,107-126`; demo direct engine path at `scripts/generate_static_abandoned_demo.py:56-81`; event timestamp fields at `app/common/schemas.py:62-85`.
- Validator callers enumerated: production engine `app/events/abandoned_object.py:230`; tests `tests/unit/test_region_validator.py:27,34-37,47,65,89`; test fake contract `tests/unit/test_abandoned_object.py:82-101`. Total direct `validate` call sites: 7.
- Completed 2026-08-01: 18/18 phase success criteria checked across phases 01-04. Phase-04 tester gate: 22/22 PASS. Final reviewer gate: 20/20 PASS. Python compilation PASS.
- Live PETS evidence: semantic HF decision executed on 16 ordered full frames, candidate `T=14.666667s`, decision `T+8s`, rejected a moving person false positive at 0.99 confidence; zero semantic alert emitted. Detector-only comparison artifact retains three alerts.
- Scope change: phase 04 permanently enabled shipped temporal Hugging Face validation with Gemma after phases 01-03 completed. Reason: production activation requested. Impact: config activation plus worker fallback/test only; thresholds, schema, timeout, temporal bounds, and unrelated runtime behavior unchanged.
- Quality-gate adjustment: full-repository collection cannot start because the provided environment lacks pre-existing `ultralytics` and `langgraph`; scoped delivery remains complete because implementation, integration, live semantic demo, secret scan, tester, and reviewer gates pass. Impact: repository-wide regression rerun remains owner follow-up.
- Artifact verification: `artifacts/static-abandoned-pets2006-summary.json`, `artifacts/static-abandoned-pets2006-detector-summary.json`, `examples/static-abandoned-pets2006-demo.mp4`, and `examples/static-abandoned-pets2006-detector-demo.mp4` exist.

## Unresolved Questions

None scoped. Repository owner must install `ultralytics` and `langgraph`, then rerun full `pytest`; done when collection succeeds and all tests pass. End-of-stream before `T+8s` does not emit a temporally validated event; disabled legacy mode remains immediate.
