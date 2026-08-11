---
title: Phase 7B.1 generic luggage runtime
status: completed
---

# Plan

1. Package the supplied two-class runtime core and self-contained Kaggle runner.
2. Apply only verified Kaggle compatibility fixes: pinned tracker API and profiler fallback.
3. Extend the Phase 7C skeleton for generic-luggage JSONL and add stationary/owner tests.
4. Run syntax, unit, contract, and review gates.
5. Submit one Kaggle kernel version; retrieve and audit outputs when the user confirms completion.

## Verification

- Syntax and embedded-core contracts: PASS.
- Core, two-tracker, warmup, Phase 7C, and cross-class NMS tests: PASS.
- Focused code review: PASS.
- Kaggle version 1: `COMPLETE`.
- Output audit: 2,189 frames, 5,019 valid JSONL observations, 17 unique tracks, no traceback.
- Runtime: 20.10 original-frame FPS; generic-luggage merge removed 21,630/35,762 duplicate detector boxes.
- Background-anchor warmup produced zero anchors, so its effectiveness is not evidenced by this clip.

## Boundaries

- No detector retraining or taxonomy-head changes.
- No abandoned-object alarm, S4, EdgeCrafter, YOLO, or VLM.
- Quality/background parameters remain provisional bundle defaults or explicit environment overrides.
