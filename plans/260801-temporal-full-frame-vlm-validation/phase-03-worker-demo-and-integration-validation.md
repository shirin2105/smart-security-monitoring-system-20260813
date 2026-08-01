---
phase: 3
title: "Worker, demo, and integration validation"
status: complete
priority: P1
effort: 3h
dependencies: [2]
---

# Phase 03: Worker, demo, and integration validation

## Context Links

- Production worker constructs validator/engine and evaluates each sampled frame: `app/cv/worker.py:56-80,85-121`.
- Current rules and static threshold defaults: `configs/event_rules.yaml:12-32`.
- Demo directly uses detector plus production engine: `scripts/generate_static_abandoned_demo.py:56-81`.
- Demo defaults and summary: `scripts/generate_static_abandoned_demo.py:22-25,101-139`.
- Existing worker and pipeline integration tests: `tests/integration/test_phase4_integration.py:1-8`, `tests/integration/test_static_abandoned_pipeline.py:1-15`.

## Overview

Expose temporal settings through production construction, set the demo's stationary threshold to 6 seconds, and verify end-to-end behavior without a demo-only validation path.

## Requirements and Architecture

- Production config supplies `temporal.enabled`, `pre_seconds=8`, `post_seconds=8`, `sample_fps=1`, `max_frames=17`; safe default is disabled for backward compatibility.
- Worker passes configuration into the existing `AbandonedObjectEngine`; no second demo engine or bespoke buffering implementation.
- Demo changes `DEFAULT_CONFIG.stationary_seconds` from 5 to 6 and enables temporal validation only when Hugging Face mode is selected. It must continue feeding every full `FrameData.image` through the same engine.
- Summary records candidate time and decision time separately as demo metadata, plus sampled frame timestamps/count, without changing `EventCandidate`.

## Related Code Files / Exclusive Ownership

- Modify: `app/cv/worker.py`, `configs/event_rules.yaml`, `scripts/generate_static_abandoned_demo.py`, `tests/integration/test_phase4_integration.py`, `tests/integration/test_static_abandoned_pipeline.py`.
- Create: `tests/integration/test_temporal_full_frame_vlm_pipeline.py` if existing integration files would exceed the project size convention.
- Delete: none.

## Implementation Steps

1. Add documented temporal config defaults and pass the block into the engine constructor.
2. Update demo threshold to exactly 6 seconds and enable the integrated temporal route for HF mode; remove assumptions that an event is emitted at maturity.
3. Extend summary/console verification with original candidate time, decision time (`>=T+8`), sampled timestamps, frame count, semantic-executed flag, and source hash.
4. Add integration tests with fake detector/validator and deterministic frames; mock only the HF network boundary.
5. Run `pytest tests/unit/test_region_validator.py tests/unit/test_abandoned_object.py tests/integration/test_static_abandoned_pipeline.py tests/integration/test_phase4_integration.py tests/integration/test_temporal_full_frame_vlm_pipeline.py` (omit final path if not created), then full `pytest`.
6. Run repository secret scan for `HF_TOKEN`, bearer values, and summary payload leakage; never require or print the real key in tests.

## Integration/E2E Matrix

| Scenario | Expected |
|---|---|
| production temporal disabled | current immediate validation/event semantics preserved |
| demo HF temporal enabled | candidate at 6s stationary; decision waits 8s; <=17 full frames |
| provider rejects | no publisher call |
| provider unavailable | fail-open event at original `T`; processing continues |
| end-of-stream before post-roll | no temporal event; explicit summary failure/reason |
| intrusion/crowd alongside pending region | unaffected candidates continue publishing |

## Risks, Security, Rollback

- High impact: config enabled globally by accident. Mitigate explicit opt-in and validated positive numeric bounds.
- High impact: tests accidentally transmit CCTV. Fake client asserts payload locally; live call remains an explicit manual demo action authorized by user.
- Medium impact: demo clip lacks 8 seconds after candidate. Preflight duration and report actionable failure; never shorten required window silently.
- Token only through `HF_TOKEN`; no CLI token option, YAML field, summary field, debug dump, or committed `.env`.
- Rollback config to disabled and revert demo metadata; production engine contract remains compatible.

## Success Criteria

- [x] Demo candidate matures at configured 6 seconds and waits through `T+8s`.
- [x] Fake HF integration observes full-scene shapes and ordered 1 FPS timestamps, max 17.
- [x] Published event preserves original `T`; demo records later decision time separately.
- [x] Non-abandoned engines and temporal-disabled behavior pass focused regressions.
- [x] Relevant suite passes (32/32), scoped secret scan finds no persisted credential, and full-suite collection limitation is isolated to pre-existing missing `ultralytics`/`langgraph` dependencies.

## Next Steps

Delivery complete. Repository owner: install missing `ultralytics`/`langgraph` dependencies and rerun full `pytest`; done when collection succeeds and all tests pass. Operations owner: review provider latency/cost before enabling temporal mode per camera.

## Unresolved Questions

None scoped. Full-repository collection remains environment-blocked by missing `ultralytics` and `langgraph`.
