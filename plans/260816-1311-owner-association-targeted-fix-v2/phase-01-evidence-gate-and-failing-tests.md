---
phase: 1
title: "Evidence gate and failing tests"
status: completed
priority: P1
effort: 2h
dependencies: []
---

# Phase 1: Evidence gate and failing tests

## Context Links

- Accepted plan: `C:/Users/trand/Downloads/Others/phase_owner_association_targeted_fix_v2_bundle/OWNER_ASSOCIATION_TARGETED_FIX_V2_PLAN.md`
- Core candidate diagnostics: `kaggle_pipeline/phase7c_kernel/phase7c_core.py:471-572`
- Trace-enabled production runner: `scripts/phase11_infer.py:60-67`
- Existing diagnostic assertions: `tests/unit/test_phase7c_v1_core.py:116-154`

## Overview

Complete diagnostics and freeze a fresh pre-fix CUDA baseline. No behavior edit in this phase.

## Requirements and architecture

- Trace each candidate: clip/frame/time, physical luggage/bbox, stationary start/confirm, person id/bbox/confidence/age, raw distance px + normalized distance, overlap seconds + temporal ratio, all score terms, score/threshold, eligibility/selection/reject reason, first/last seen and before/at/after-stationary flags, fragmentation indicator, competing-person count.
- Preserve diagnostic bounding (existing bbox samples are capped at five: `kaggle_pipeline/phase7c_kernel/phase7c_core.py:523-537`) and event behavior.
- Data flow: track rows → per-candidate measurements → scorer → structured trace JSONL → two-row evidence table. No trace data feeds selection.

## Related Code Files / ownership

- Modify only if fields absent: `kaggle_pipeline/phase7c_kernel/phase7c_core.py`, `scripts/phase11_infer.py`, trace extraction/analyzer identified by re-grep.
- Modify diagnostic tests only: `tests/unit/test_phase7c_v1_core.py` or one existing trace test file; do not create a second owner subsystem.
- Output: plan-local/report artifact paths chosen by implementation, never overwrite prior Phase11b2 evidence.

## Tests Before / implementation steps

1. Re-grep and diff dirty files; preserve user changes. Add failing tests for missing score components and trace-disabled event equivalence.
2. Add only missing diagnostic fields. Run compile plus targeted diagnostic tests.
3. Run real CUDA fresh traces in order: `LeftBag`, then `LeftBag_AtChair`; use the existing Phase11 inference boundary (`scripts/phase11_infer.py:95-160`).
4. Populate: Clip, best candidate/id, best score, threshold, distance px/norm, inside/near/overlap terms, temporal overlap, fragmented, competing people, exact reject.
5. Answer all ten root-cause questions. Stop if either row lacks evidence; status `OWNER_ROOT_CAUSE_NOT_PROVEN`.

## Success Criteria

- [ ] Diagnostic tests fail first, then pass; tracing on/off emits identical lifecycle events.
- [ ] Both positive rows are fresh, CUDA-backed, reproducible, and complete.
- [ ] Root cause maps to exactly one allowed class A-E; threshold class E allowed only with measured positive/negative separation.

## Work performed and evidence

- [x] Diagnostic RED recorded: 2 expected failures for missing score-component fields.
- [x] Diagnostic GREEN recorded: 2 passed after behavior-neutral instrumentation.
- [x] Fresh CUDA traces completed for `LeftBag` and `LeftBag_AtChair` with candidate-level schema rows.
- [x] Evidence table populated in `artifacts/owner-association-v2/trusted_positive_analysis.csv`.
- [x] Root cause classified as Class A `SCORING_NORMALIZATION_DEFECT`.

Execution evidence satisfies the diagnostic gate. Original product-oriented success criteria remain unchecked; this plan ended rejected downstream.

## Risk Assessment / rollback / security

| Risk | L×I | Mitigation |
|---|---|---|
| Diagnostics accidentally alter selection | M×High | Event-equivalence test; no diagnostic value read by scorer |
| Stale artifacts mistaken for baseline | M×High | New output dir, run manifest/checksums, CUDA/device/commit recorded |
| Dirty-file overwrite | M×High | Re-grep + diff before edit; scoped patch only |

Rollback diagnostic code only; retain evidence. No sensitive video content beyond local artifacts; do not publish frames/logs.

## Next Steps

Phase 2 blocked until evidence gate passes. Unresolved questions: none; failure produces terminal status, not speculation.
