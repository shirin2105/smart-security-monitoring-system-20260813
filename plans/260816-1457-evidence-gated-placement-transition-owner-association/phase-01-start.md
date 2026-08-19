---
phase: 1
title: "Feature contract and TDD discriminators"
status: completed
priority: P1
effort: 3h
dependencies: []
---

# Phase 1: Feature contract and TDD discriminators

## Context Links

- Owner model/diagnostics: `kaggle_pipeline/phase7c_kernel/phase7c_core.py:104-118,472-651`
- Synchronized rows: `kaggle_pipeline/phase7c_kernel/phase7c_core.py:481-516`
- Trace projection: `app/cv/events/phase7c_owner_association_trace.py:18-61`
- Existing tests: `tests/unit/test_phase7c_v1_core.py:53-154`; `tests/unit/test_phase11b_trace.py:22-55`

## Overview / Requirements

Define behavior-neutral placement-transition features from existing same-frame rows. Inputs: centers, bboxes, timestamps, stationary start, quality profiles. Transform with finite differences over the final contiguous synchronized segment; normalize by median person bbox diagonal. Duplicate/non-finite timestamps invalidate evidence; a gap >0.5 s truncates the segment; require >=4 samples, >=3 intervals and >=0.6 s support. Derive bag motion, moving-interval alignment, direction cosine and relative-offset P90 spread. The frozen diagnostic predicate requires bag motion >=0.25, aligned-moving ratio >=0.60, median aligned cosine >=0.50, and offset spread <=0.35. Missing/sparse support fails closed. No interpolation, selection change, or public contract change.

## Architecture / Data Flow

`physical.rows` + person rows → existing frame intersection (`phase7c_core.py:487-516`) → pure helper → fixed-shape scalar candidate diagnostics → separate `placement-diagnostics-v1` sidecar. Diagnostics never feed score/eligibility/selection/owner timestamps/events in this phase. The existing 26-field owner-association JSONL schema and `OWNER_ASSOC_FIELDS` remain key-for-key unchanged. Sidecar rows are bounded; cumulative debug files remain run-duration dependent.

## Related Code Files / Ownership

| Action | File | Purpose |
|---|---|---|
| Modify | `kaggle_pipeline/phase7c_kernel/phase7c_core.py` | pure helper + diagnostic fields |
| Create | `app/cv/events/phase7c_placement_diagnostic_trace.py` | versioned sidecar schema/projection |
| Modify | `tests/unit/test_phase7c_v1_core.py` | synthetic RED/GREEN |
| Modify | `tests/unit/test_phase11b_trace.py` | sidecar schema plus legacy exact-26-field/neutrality regression |

No parallel owner. Phase 3 may receive sequential ownership of core/tests.

## Tests Before / Matrix

| Scenario | Required result |
|---|---|
| Genuine co-motion→placement | sufficient, placement-like |
| Passerby near bag | motion/offset mismatch |
| Crossing paths | direction/offset mismatch |
| Sparse/fragmented | insufficient, fail closed |
| Already-stationary bag | transition absent |
| Picked-up | no alert qualification; pickup semantics unchanged |

Also test scale/translation invariance, gaps, duplicate timestamps, zero velocity, deterministic ordering, and trace on/off identical normalized events/selected owner.

## Implementation Steps

1. Inspect dirty diff; add table-driven RED tests.
2. Implement smallest NumPy pure helper; no history copies beyond bounded summaries.
3. Project fields to a separate versioned sidecar and prove behavior neutrality.
4. Run compile and targeted tests.

## Success Criteria / Gate

- [x] RED then GREEN for six scenarios.
- [x] Trace on/off event and owner-selection equivalence.
- [x] No score, threshold, lifecycle, ROI, stationary, or public contract delta.
- [x] `python -m compileall kaggle_pipeline/phase7c_kernel app/cv/events` and targeted placement/trace tests pass.

## Risk Assessment / Rollback

| Risk | L×I | Mitigation |
|---|---|---|
| Gaps invent co-motion | M×High | no interpolation; contiguous support |
| Diagnostic leakage | Low×High | output-equivalence test |
| Perspective overfit | M×High | normalization + invariance tests + real gate |
| Dirty overwrite | M×High | narrow diff-aware patches |

Diagnostic rollback removes helper/plumbing/sidecar if legacy schema, trace-off equivalence, lifecycle counts, bounded memory, finite JSON, or determinism fails. Local bounded numeric traces only.

## Unresolved Questions

None.
