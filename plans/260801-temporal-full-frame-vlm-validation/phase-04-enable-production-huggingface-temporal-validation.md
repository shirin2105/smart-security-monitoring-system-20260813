---
phase: 4
title: "Enable production Hugging Face temporal validation"
status: complete
priority: P1
effort: "1h"
dependencies: [3]
---

# Phase 04: Enable production Hugging Face temporal validation

## Context Links

- Shipped rules currently disable temporal validation and VLM while already naming Gemma: `configs/event_rules.yaml:23-34`.
- `AppConfig.event_rules` reloads `event_rules.yaml` on access: `app/config.py:12-17,27-29`.
- Worker reads the abandoned-object block, constructs the validator, and injects it into the engine: `app/cv/worker.py:56-63,75-80`.
- Worker fallback model diverges from factory/Gemma default: `app/cv/worker.py:61-63`; `app/vlm/region_validator.py:254-262`.
- Existing worker integration asserts the old disabled production default: `tests/integration/test_temporal_worker_eos.py:47-56`.

## Overview

Permanently activate the already-implemented production temporal Hugging Face route using `google/gemma-3-4b-it`. Configuration and regression proof only; no policy, threshold, schema, token persistence, or live inference work.

## Requirements

- Set `abandoned_object.temporal.enabled: true` and `abandoned_object.vlm.mode: huggingface`; retain all temporal limits, thresholds, timeout, and `model: google/gemma-3-4b-it` unchanged.
- Change only the worker's missing-model fallback to `google/gemma-3-4b-it`, matching the factory default.
- Test the real config-to-worker path without replacing `settings.event_rules` or the validator factory. Remove `HF_TOKEN` for isolation and make any HTTP attempt fail the test; construction must make no request.

## Architecture and Data Flow

`configs/event_rules.yaml` -> `AppConfig.load_yaml()` -> `settings.event_rules["abandoned_object"]` -> worker reads `temporal` through `AbandonedObjectEngine` and `vlm` through `create_region_validator()` -> `HuggingFaceRegionValidator(model=Gemma)` injected into the engine. Runtime frames later enter the existing bounded temporal pipeline; missing `HF_TOKEN` yields the existing unavailable/fail-open result without network (`app/vlm/region_validator.py:183-186`).

## Related Code Files / Exclusive Ownership

- Modify: `configs/event_rules.yaml`, `app/cv/worker.py`.
- Create: `tests/integration/test_production_vlm_configuration.py`.
- Delete: none. Do not edit threshold, policy, schema, or credential files.

## Implementation Steps

1. Flip only the two activation values in `configs/event_rules.yaml`; preserve Gemma and every numeric setting.
2. Align `CVWorker`'s absent-model fallback with Gemma.
3. Add one integration test constructing `CVWorker` from the repository config (inject detector only if needed to avoid model loading). Assert `engine.temporal_enabled is True`, validator type is Hugging Face, and validator model equals Gemma. Forbid network at the HTTP boundary and assert zero calls during construction.
4. Update the old production-default assertion at `tests/integration/test_temporal_worker_eos.py:47-56` or supersede it in the new test so no test claims temporal remains disabled.
5. Run focused config/worker and validator tests, then full pytest when optional dependencies are installed. Scan tracked files for token-like values; `HF_TOKEN` name is allowed, values are not.

## Test Matrix

| Level | Scenario | Observable result |
|---|---|---|
| Integration | real shipped YAML -> settings -> worker | temporal enabled; actual HF validator; Gemma model |
| Integration | `HF_TOKEN` absent; HTTP forbidden | worker constructs with zero network calls; no credential persisted |
| Unit/regression | validator missing-token behavior | unavailable result remains deterministic and no network |
| Regression | existing temporal limits and non-abandoned engines | values/engine registration unchanged |

## Risks, Security, Compatibility, Rollback

- High likelihood/high impact: production now attempts semantic validation when a temporal candidate matures. Mitigate existing 8s timeout, bounded 17-frame/12 MB request, one terminal decision, missing-token no-network behavior; operational latency/cost monitoring is outside this config-only phase.
- Medium likelihood/high impact: an integration test accidentally calls HF. Mitigate deleting `HF_TOKEN`, replacing/guarding the HTTP boundary with a fail-fast spy, and asserting call count zero.
- Compatibility: intentional shipped-default change only. Explicit external configs selecting disabled/heuristic remain supported; public schemas, thresholds, event contracts, and stored data unchanged.
- Rollback: set `temporal.enabled: false`, `vlm.mode: disabled`, and restore the prior worker fallback. No cascading cleanup or data migration.

## Success Criteria

- [x] Repository YAML observably selects temporal + Hugging Face + `google/gemma-3-4b-it`.
- [x] A real-config `CVWorker` exposes `temporal_enabled=True` and a Hugging Face validator configured with Gemma.
- [x] Focused test proves construction and missing-token validation cannot access network; no token value is stored.
- [x] No threshold, policy, schema, timeout, temporal bound, or unrelated runtime behavior changes.
- [x] Focused tests pass; full-suite result reported without hiding dependency/collection failures.

## Validation Result

- 2026-08-01: implementation verified in shipped YAML, worker fallback, and real-config integration test. Tester gate 22/22 PASS. Final reviewer gate 20/20 PASS. Python compilation PASS. One non-functional pytest cache-permission warning.

## Unresolved Questions

None scoped.
