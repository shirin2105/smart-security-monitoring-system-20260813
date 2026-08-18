# Phase 11B-FINAL Report

## Decision and policy

All four candidate positives, including `LeftBag_PickedUp`, remain `AMBIGUOUS_NEEDS_HUMAN`. They are excluded from tuning. The frozen Phase 11 benchmark `CENTRAL_ROI` is unchanged; no camera overrides or diagnostic no-ROI default were authorized.

## Refrozen benchmark

- Trusted positives: 0; positive metrics and first-failing-stage distribution: not computable.
- Generic negatives completed: 15/15 under the frozen benchmark ROI.
- Abandoned START count: 0 (PASS); false alarms/hour: 0.000 across 652.96s.
- Provenance: `artifacts\phase11b_final\production-roi-run-v2.json` validates clip completion, ROI, prediction hash, event-rule hash, and inference-script hash.
- Semantic negative categories remain unlabeled and not covered.

## Scope lock

No owner, threshold, detector, tracker, stationary, ROI, or Phase 12 change is authorized. Authoritative human/product adjudication remains required.

## FINAL STATUS

ROI_POLICY_UNRESOLVED
