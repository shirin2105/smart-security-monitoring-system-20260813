---
phase: 1
title: "Temporal validation contract"
status: complete
priority: P1
effort: 3h
dependencies: []
---

# Phase 01: Temporal validation contract

## Context Links

- Existing protocol and one-crop adapters: `app/vlm/region_validator.py:17-45`.
- HF token read from `HF_TOKEN`: `app/vlm/region_validator.py:57-65`.
- Current single-image payload and bounded timeout: `app/vlm/region_validator.py:107-128`.
- Existing adapter tests: `tests/unit/test_region_validator.py:26-96`.

## Overview

Add a temporal full-scene validation contract while retaining the single-crop interface for existing callers and disabled/heuristic modes.

## Requirements and Architecture

- Input: ordered samples containing captured timestamp plus full BGR frame, immutable candidate region, and event time `T`.
- Transform: validate count `1..17`, chronological order, frame validity, JPEG limits; encode each full frame; prompt asks whether the scene sequence shows an object being left/abandoned.
- Output: existing `VLMValidationResult`; no token, frame, payload, or raw response persisted.
- Prefer `validate_temporal(frames, region, event_time)` added to the protocol/adapters. Default bridge selects the event-nearest frame and invokes `validate`, preserving custom validators and old tests.
- HF adapter sends all ordered images in one OpenAI-compatible message; strict JSON parsing and fail-open `unavailable` behavior stay unchanged.

## Related Code Files / Ownership

- Modify only `app/vlm/region_validator.py` and `tests/unit/test_region_validator.py`.
- Create/delete: none.

## Implementation Steps

1. Define a small typed temporal-frame input and temporal method; do not change `VLMValidationResult` or public event schema.
2. Implement compatibility bridge for disabled, heuristic, and third-party single-image validators.
3. Update HF prompt/payload builder for ordered full frames; enforce max 17 and existing per-image dimension/byte caps.
4. Keep `HF_TOKEN` environment lookup at construction/call boundary; redact exceptions and never serialize headers/payload.
5. Add unit tests before implementation for order, count, malformed frames, multi-image payload, missing token, timeout/malformed response, and old `validate` behavior.

## Test Matrix

| Scenario | Expected |
|---|---|
| 17 ordered frames | 17 image parts, temporal prompt, strict parsed verdict |
| >17 or unordered | deterministic validation error/unavailable; no request |
| no `HF_TOKEN` | unavailable; client never called |
| old custom validator | single-image bridge works without signature break |
| provider failure | unavailable; exception/token/payload absent from result |

## Risks, Security, Rollback

- High impact: request exceeds provider limits. Mitigate hard count, resize/JPEG caps, one request, explicit test of encoded payload size behavior.
- Medium impact: protocol break for injected validators. Mitigate runtime capability check/adapter bridge and retain `validate`.
- Full-frame upload is explicitly authorized, but only temporal mode may do it. Token stays environment-only and excluded from logs/config/summary.
- Rollback restores one-image HF construction; compatibility method can remain harmless if callers already adopt it.

## Success Criteria

- [x] Existing validator tests remain green.
- [x] One HF request contains ordered full-frame image parts, maximum 17.
- [x] No-token path performs zero network calls.
- [x] Direct single-crop callers remain compatible.

## Next Steps

Phase 02 consumes the frozen temporal contract.

## Unresolved Questions

None.
