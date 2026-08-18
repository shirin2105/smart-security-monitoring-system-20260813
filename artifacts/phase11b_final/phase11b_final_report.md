# Phase 11B-FINAL Report

## 1. Clip decisions

All four current positives are `AMBIGUOUS_NEEDS_HUMAN`, excluded from tuning. See `evaluation/phase11b_final/adjudication.csv`.
`LeftBag_PickedUp` was explicitly reviewed and remains ambiguous; no filename-only decision was made.

## 2. Final ROI policy

- ROI version: `phase11b-final-roi-v1`.
- Production/default: frozen pixel `CENTRAL_ROI`; unchanged.
- Camera overrides: none. Diagnostic no-ROI is not a production default.

## 3. Refrozen benchmark

- In-policy positives: 0.
- Generic negatives: 15/15.
- TP: 0; FP: 0; FN: 0.
- Recall/F1/delay/duplicate: not computable without trusted positives/events.
- False alarms/hour: 0.000 across 652.96s.

## 4. First failing stage

- Distribution: not computable; no in-policy positives.
- Counterfactual Phase 11B.2 evidence exposed `OWNER_NOT_ASSOCIATED`, but it cannot authorize tuning before policy adjudication.

## 5. Targeted fix

- Authorized: no.
- Exact fix: none. No threshold, owner, detector, tracker, stationary, or ROI default change.

## 6. Negative safety

- 15 generic negatives rerun under production/default ROI.
- Abandoned START count: 0 — PASS.
- Semantic negative categories remain unlabeled and NOT COVERED.

## 7. Non-regression

- See `test_handoff.md`.

## 8. Limitations

- Authoritative human/product ROI adjudication unavailable.
- External Gemini video analysis unavailable; local agent review cannot decide product policy.
- Hardware: real CUDA DEIMv2 inference completed.

## 9. FINAL STATUS

ROI_POLICY_UNRESOLVED
