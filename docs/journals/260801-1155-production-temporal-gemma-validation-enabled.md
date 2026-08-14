# Production Temporal Gemma Validation Is Now Permanently Enabled

**Date**: 2026-08-01 11:55
**Severity**: Medium
**Component**: Abandoned-object temporal VLM validation
**Status**: Resolved

## What Happened

We made temporal Hugging Face validation the production default. `configs/event_rules.yaml` now sets `temporal.enabled: true`, an inclusive `pre_seconds: 8` / `post_seconds: 8` window at 1 FPS, `max_frames: 17`, `buffer_max_dimension: 480`, and `buffer_byte_ceiling: 12000000`. The VLM block now selects `mode: huggingface`, `model: google/gemma-3-4b-it`, and an 8-second HTTP timeout. The worker consumes those values directly; its fallback model and timeout match production, while a missing VLM block still falls back to `disabled` instead of silently enabling a network service.

## The Brutal Truth

Calling this “validation” hides a painful operational compromise. Every candidate now waits eight seconds for post-roll and then performs a synchronous remote call that may block the camera worker for up to another eight seconds. That can add roughly 16 seconds after candidate maturity before a decision is available. We accepted this because abandonment is temporal; pretending a crop or heuristic could answer it was worse.

## Technical Details

Worker construction performs no network access. `HuggingFaceRegionValidator` reads `HF_TOKEN`, but creates `httpx.Client` only inside `validate_temporal()`. With no token it immediately returns `verdict="unavailable"` and `reason="huggingface_unavailable:missing_token"`; no credential is recorded here. The engine is deliberately fail-open: only `verdict == "rejected"` suppresses an event, so missing tokens, timeouts, malformed responses, and provider failures allow the detector candidate through.

## What We Tried

- Rejected keeping temporal mode opt-in: production would continue running weaker semantics by default.
- Rejected heuristic/local validation as the production substitute: it cannot establish that an object was left behind.
- Kept conservative worker fallback behavior for absent configuration and no startup request, avoiding an accidental dependency on provider availability during boot.

## Root Cause Analysis

The previous configuration treated the strongest semantic check as demo-only even though the implementation and live evidence were ready. The fundamental mistake was separating “implemented” from “actually enabled,” leaving production behavior weaker than the system we claimed to operate.

## Lessons Learned

Production defaults are part of the feature, not deployment trivia. Remote inference also needs explicit latency and failure semantics: here the price is synchronous +8-second post-roll plus up to 8 seconds of provider wait, and fail-open means availability wins over semantic certainty.

## Next Steps

- Deployment owner: provide `HF_TOKEN` through the secret manager before the next production rollout; never commit or log it.
- Operations owner: monitor worker processing latency, provider timeout rate, and `huggingface_unavailable:*` reasons from first rollout onward.
- CV owner: move remote validation off the synchronous worker path if camera backlog appears.
- Test/review status: focused compile passed; 34 relevant unit/integration/demo tests passed in 1.29s, including production construction without network and missing-token fail-open. Scoped review found no release-blocking correctness issue; numeric coverage remains uncollected because `pytest-cov` is unavailable.
