# Phase 11B.2 ROI Audit Exposed the Next Blocker

**Date**: 2026-08-16 07:59
**Severity**: High
**Component**: CV abandoned-object benchmark pipeline
**Status**: Blocked

## What Happened

All four positive abandoned-object clips failed the frozen valid-floor ROI gate: 0/4 passed. Coordinate tracing and eight before/after overlays showed the boxes were restored to the original 384x288 frame correctly, the ROI remained in pixel coordinates, and the bottom-center test point was computed correctly. The data and the frozen benchmark policy disagree; this was not a transform bug.

## The Brutal Truth

This was frustrating because the obvious-looking fix—remove the ROI—would have made the headline failure disappear while quietly violating the benchmark contract. That would have been benchmark tampering dressed up as progress. The useful relief is that the audit finally replaced speculation with reproducible evidence.

## Technical Details

The frozen run rejected 4/4 positives. The final opt-in counterfactual, enabled only with `PHASE11B2_DISABLE_ABANDONED_ROI=1`, passed the ROI for 4/4, then exposed the actual next failure: `OWNER_NOT_ASSOCIATED` on 4/4, with zero events emitted. The safety run covered all 15 manifest-classified generic negatives and emitted zero `ABANDONED_OBJECT` START alerts. Full CV regression completed with 260 passed, 1 skipped, and 8 subtests passed.

## What We Tried

We first proposed removing the abandoned ROI. That proposal was rejected because Phase 11's frozen benchmark contract explicitly preserves the central valid-floor restriction. We rejected polygon enlargement and test-point changes for the same reason. We instead added an explicit diagnostic-only counterfactual, leaving production and benchmark defaults untouched.

## Root Cause Analysis

The root cause is a benchmark-policy mismatch: positive GT placements sit outside the frozen ROI. Removing that gate does not solve abandoned-object detection; it merely advances every positive to failed owner association.

## Lessons Learned

Never tune away a failed gate before proving whether coordinates, GT, or policy are wrong. Counterfactuals must be opt-in and must not mutate frozen defaults. A green regression suite cannot adjudicate semantic ground truth.

## Next Steps

The CV/benchmark owner must obtain human review of the GT and ROI overlays before the next benchmark re-freeze. After adjudication, the owner must either revise the ROI contract or exclude/relabel out-of-policy GT; only then should owner-association work proceed. Timeline: before Phase 11B.3 acceptance.

**Status:** BLOCKED
**Summary:** ROI math is correct; frozen policy rejects 4/4 positives, while an opt-in no-ROI counterfactual exposes `OWNER_NOT_ASSOCIATED` on 4/4 without alerts on 15/15 generic negatives.
**Concerns/Blockers:** Human GT/ROI adjudication remains unresolved; automated and agent visual evidence cannot authorize a benchmark contract change.
