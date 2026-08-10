---
title: Phase 7B class-wise ByteTrack and Phase 7C skeleton
status: completed
---

# Plan

1. Package the supplied `phase7b_core.py`, tests, and Kaggle video runner without detector retraining or architecture changes.
2. Add a local Phase 7C data package: JSONL loading, trajectory/displacement helpers, threshold-free stationary features, and owner-association interface.
3. Add deterministic unit tests for identifiers, history, JSONL, displacement, stationary features, and interface contracts.
4. Compile and run focused tests; review for forbidden event emission and dependencies.

## Constraints

- Use `trackers.ByteTrackTracker`; never `sv.ByteTrack`.
- Keep person/backpack/handbag/suitcase trackers class-isolated.
- No S4, EdgeCrafter, YOLO, VLM, retraining, threshold tuning, or abandoned-object event emission.
- Do not wait for Kaggle execution.

## Success

- Kaggle runner and command are ready.
- Focused local tests pass.
- Phase 7C skeleton consumes Phase 7B JSONL without making deployment decisions.

## Verification

- Python compile: PASS.
- Phase 7B core assertions: 3 PASS.
- Focused class isolation and Phase 7C unit tests: 7 PASS.
- `trackers==2.5.0.post0` API contract inspected and compatibility fix reviewed: PASS.
- Kaggle video execution remains an external runtime TODO and was not awaited by design.
