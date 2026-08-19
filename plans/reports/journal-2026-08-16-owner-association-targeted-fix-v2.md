# Owner Scoring Fix Failed the Negative Gate

**Date**: 2026-08-16 13:57
**Severity**: High
**Component**: Phase7C abandoned-object owner association
**Status**: Resolved

## What Happened

Fresh CUDA traces showed both trusted owners were eligible, close, temporally overlapping, and unfragmented, but the frozen scorer rejected them below `0.60`. We tried one targeted class-A change in `kaggle_pipeline/phase7c_kernel/phase7c_core.py`: replace the 65% whole-history containment term with normalized closest approach. `LeftBag` improved from `0.1957` to `0.785` and emitted one START. `LeftBag_AtChair` improved from `0.2417` to `0.7818`, selected an owner, then still emitted zero START because `OWNER_AWAY_NOT_REACHED` became the next failing stage.

## The Brutal Truth

The fix made the scorer look smarter on positives and proved unsafe almost immediately. That is frustrating because the first result felt like a breakthrough, but it was a trap: optimizing the evidence we wanted created production-grade false alarms on ordinary footage. Shipping it would have traded one known miss for noisy alerts that destroy operator trust.

## Technical Details

The 15/15 generic-negative CUDA run moved from zero abandoned STARTs to two, both on `WalkByShop1front`. `LeftBag_PickedUp` stayed at zero START. Focused tests passed 15/15; CV regressions passed 83/83. Full unit results were 326 passed, one skipped, eight unrelated failures. Evidence is preserved in `artifacts/owner-association-v2/final_report.md`, `trusted_positive_analysis.csv`, and `attempted-fix.patch`. Provenance is retrospective: hashes bind run artifacts, but attempted-fix source identity was not captured during execution.

## What We Tried

We chose closest-approach normalization over lowering the threshold, widening history, adding continuity state, or combining fallbacks because traces isolated a scoring defect and the plan allowed exactly one fix class. We rejected the implementation after the mandatory negative gate; no threshold tuning or second behavior change was attempted.

## Root Cause Analysis

The original scorer overweights strict containment across the entire pre-stationary history. The replacement overcorrected by rewarding a single close encounter, allowing a passerby in `WalkByShop1front` to become an owner. The mistake was treating positive separation as sufficient before proving negative separation.

## Lessons Learned

Never accept owner scoring from positive clips alone. A plausible geometric term is not a safe ownership signal. Capture source identity at execution time, and run the cheapest representative negative gate before broader validation.

## Next Steps

- CV owner: keep the production scorer rolled back and diagnostics intact, effective immediately.
- CV owner: do not implement a second fix in this work item. Any new approach requires a new evidence baseline, explicit authorization, and positive/negative separation proof.
- Product/data owner: provide better owner-exit/association annotations before another scoring attempt; timeline TBD.

Final status: `OWNER_FIX_REJECTED_FALSE_POSITIVES`.
