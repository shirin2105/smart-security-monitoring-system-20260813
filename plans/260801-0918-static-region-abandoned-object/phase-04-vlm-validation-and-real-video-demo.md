---
phase: 4
title: "VLM validation and real-video demo"
status: completed
priority: P2
effort: 3h
dependencies: [3]
---

# Phase 04: VLM validation and real-video demo

## Context Links

- `app/common/enums.py:12-15` already distinguishes CV and VLM sources.
- `scripts/process_real_abandoned_with_drop.py:22-24,66-108` uses real footage but injects a synthetic bag/detection.
- `tests/clips/vtest.avi` exists and is the canonical real-data input.
- `requirements.txt:27-31` already includes `httpx`; no new SDK is required for a small HF adapter.

## Overview

Add an optional validator seam with offline/local and Hugging Face implementations, then replace the injected demo with a deterministic run over unmodified real video.

## Requirements

- Functional: validation modes `disabled`, `local`, `huggingface`; local fallback on missing token, timeout, rate limit, malformed response, or provider error; annotate demo with regions, elapsed time, person count, verdict, alert.
- Non-functional: no secrets in YAML/artifacts; bounded HTTP timeout; crop/minimize outbound pixels; CV pipeline continues when VLM unavailable; demo command returns nonzero when artifacts are invalid.

## Architecture and data flow

Mature region + cropped evidence -> `RegionValidator` protocol. `disabled` accepts CV verdict; `local` applies deterministic image/shape sanity rules; `huggingface` sends only crop with token from environment and parses strict result. Any remote failure -> local result with `unavailable` metadata. Accepted result reaches event emission; rejected result remains observable but emits no event. Demo: original `vtest.avi` -> production pipeline -> overlays -> MP4 + JSON summary (clip hash, config, FPS, alert frame/time, events, VLM mode).

## Related Code Files / Ownership

- Create: `app/vlm/region_validator.py`, `tests/unit/test_region_validator.py`, `scripts/generate_static_abandoned_demo.py`
- Modify: `app/config.py`, `configs/cameras.yaml`
- Generate (not hand-edit): `examples/static-abandoned-vtest-demo.mp4`, `artifacts/static-abandoned-vtest-summary.json`
- Delete: none

## Implementation Steps

1. Define validator protocol plus disabled/local implementations; unit-test deterministic verdicts.
2. Add HF HTTP adapter using environment token only, strict timeout/status/schema handling, and local fallback. Mock only the network boundary in unit tests; real demo defaults offline/local.
3. Add config selection and dependency injection. Record provider/model/verdict without exposing token or raw response.
4. Implement demo runner against untouched `tests/clips/vtest.avi`; timestamps derive from frame/FPS. Do not append fabricated detections or paint objects into source frames.
5. Validate output writer opened, output frame count matches input, JSON contains at least one event or explicitly fails calibration, and rerun produces identical alert frame/time.

## Todo List

- [x] Add validator/fallback tests.
- [x] Implement config/provider selection.
- [x] Build real-video demo runner.
- [x] Run `pytest tests/unit/test_region_validator.py` and full relevant feature suite.
- [x] Run real-data demo repeatedly and compare deterministic summaries.

## Success Criteria

- [x] No-token environment completes in local mode with no network access.
- [x] HF timeout/error deterministically falls back and does not suppress CV processing.
- [x] Generated MP4 opens, has source dimensions/FPS/frame count, and contains region/alert overlays.
- [x] JSON names source clip, hash, thresholds, alert frame/time, verdict, and event candidate IDs.
- [x] Two runs have identical alert frame/time and event count.

## Risk Assessment

- High likelihood/high impact: remote VLM latency/cost stalls frames. Mitigation: invoke once per matured region, crop, timeout, cache by region, local fallback; never call per frame.
- Medium likelihood/high impact: VLM rejects valid CV event. Mitigation: default disabled/fail-open; make rejection gating explicit config, default observational.
- High likelihood/medium impact: real clip does not meet initial thresholds. Mitigation: calibration command reports masks/regions; tune documented config, never inject detections.

## Security Considerations

Environment-only HF token; redact logs; transmit crop only with explicit remote mode; set size limits and TLS endpoint; never commit response payloads containing provider metadata.

## Rollback

Set VLM mode `disabled`; demo artifacts are removable/generated. Revert adapter/config without touching CV/event contracts.

## Next Steps

Review demo and test evidence. Promote tuned thresholds per camera only after false-positive evaluation on negative clips.

## Unresolved Questions

None blocking. HF model/endpoint stays deployment-configured; default implementation must function locally without it.
