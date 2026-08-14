---
phase: 1
title: "Freeze baseline and contract"
status: completed
priority: P1
effort: 1d
dependencies: [260810-phase8-cv-e2e-validation]
---

# Phase 1: Freeze baseline and contract

## Context Links

- Bundle mandatory steps 1-4; existing Phase 8 plan; `docs/system-architecture.md:3-29`; contract `app/cv/contracts/validation.py:7-123`.

## Overview

Record immutable runtime/config/test evidence before migration. Confirm existing detector/tracker/store/contract behavior rather than redesigning it.

Progress: complete. Baseline/contract characterization recorded; final video evidence contains source hashes/config/artifacts. Required CV suite passes 78 + 8 subtests.

## Implementation Tracking

- [x] Baseline document and characterization tests implemented.
- [x] Frozen runtime, thresholds, contract, commands, and known missing evidence recorded.
- [x] Phase 8 video artifact IDs/hashes and PASS evidence obtained for required Phase 9 inputs.

## Requirements and Architecture

- Capture checkpoint/config hashes, detector/tracker classes, Phase7C + intrusion/crowd thresholds, commands/results in baseline doc.
- Trace current data: `FrameData` enters detector (`app/cv/detector.py:55`), tracker (`app/cv/tracker.py:53`), store (`app/cv/track_store.py:42-64`), then engines (`app/cv/worker.py:116-140`).
- Freeze cv-event-v1 required fields and three event builders; no schema-breaking rename.

## Related Code Files / Ownership

- Create: `docs/phase9/baseline.md` (Phase 1 only).
- Create: `tests/integration/test_unified_cv_baseline.py` (Phase 1 only).
- Read only: detector, tracker, store, contract, Phase 8 results/configs.

## Implementation Steps

1. Retrieve Phase 8 completed outputs; record missing evidence explicitly if blocked.
2. Run current focused/full tests; record commands, environment, counts, failures.
3. Add characterization tests: detector once/frame, shared tracker/store identity, schema serialization/builders.
4. Freeze current values; prohibit weights/threshold changes absent a reproduced bug.

## Test Matrix / Success Criteria

| Level | Scenario | Observable gate |
|---|---|---|
| Unit | CVEvent builders/validation/JSON round trip | all three types accepted; invalid lifecycle/evidence rejected |
| Integration | worker N processed frames | detector calls = N; same store snapshot reaches all engines |
| Regression | existing suite | no new failure; result recorded in baseline |

- [x] Baseline includes artifact IDs/hashes, thresholds, commands, results, Phase 8 input status.
- [x] All live paths/symbols re-grepped and cited before implementation.

## Risks / Rollback / Security

- High likelihood × High impact: incomplete Phase 8 baseline hides regressions. Mitigation: block Phase 1 completion; do not infer PASS.
- Medium × High: asset drift. Mitigation: SHA-256 + config snapshot; never commit weights/secrets.
- Rollback: remove only new doc/test; runtime unchanged.

## Next Steps

Phase 2 completed after baseline and contract gates passed.
