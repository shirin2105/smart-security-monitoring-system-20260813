---
title: Phase 7C v1 abandoned-object reasoning
status: completed
---

# Plan

1. [x] Preserve the supplied offline reasoning core and Kaggle runner under `kaggle_pipeline/phase7c_kernel/`.
2. [x] Add Kaggle metadata that attaches the completed Phase 7B.1 output and ABODA source video, with GPU disabled.
3. [x] Add a backend-safe candidate contract, per-camera configuration example, local replay documentation, and event-level evaluator.
4. [x] Add positive and negative tests for quality, stitching, stationary hold, owner association, owner return, ROI, event serialization, and metrics.
5. [x] Run compile, unit, offline replay, package, and code-review gates.
6. [x] Push one Kaggle kernel version; execution result intentionally not awaited.

## Locked boundaries

- Input is Phase 7B.1 `tracks_v4.jsonl`; detector and model training are not rerun.
- Emit only `ABANDONED_OBJECT_CANDIDATE`; do not confirm or escalate an alarm.
- No S4, EdgeCrafter, YOLO, VLM, Re-ID, or cross-camera logic.
- Bundle thresholds remain baseline defaults and are not tuned from one clip.

## Acceptance — verified complete

- [x] Compile: 19/19 checks pass; scenarios: 19/19 pass.
- [x] Actual replay: 5,019 rows / 17 tracks; quality pass person/luggage 10/2; physical=1, stitch=1, association=1; candidate `AO_0001` emitted.
- [x] Candidate evaluator safe; no labels invented for metrics.
- [x] Negative-path suite covers stationary, owner-away, owner-return, ROI, serialization, stitch, quality, and metrics gates.
- [x] Code review: PASS.
- [x] Kaggle kernel v1 pushed: `shirin21st/deimv2-phase-7c-v1-abandoned-reasoning`; remote result intentionally not awaited.
