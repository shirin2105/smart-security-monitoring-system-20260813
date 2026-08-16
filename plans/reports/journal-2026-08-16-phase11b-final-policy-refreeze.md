# Phase 11B-FINAL Policy Refreeze Ended Without Positive Evidence

**Date**: 2026-08-16 09:29
**Severity**: High
**Component**: Phase 11B abandoned-object benchmark policy
**Status**: Blocked

## What Happened

We completed Phase 11B-FINAL in scope and refroze the benchmark without changing the production `CENTRAL_ROI`. Human adjudication left all four candidate positives, including `LeftBag_PickedUp`, as `AMBIGUOUS_NEEDS_HUMAN`; therefore the trusted-positive set is empty. We rejected filename-based labeling, a diagnostic no-ROI default, camera overrides, threshold tuning, a targeted pipeline fix, and Phase 12 because none had authorization or defensible positive ground truth.

## The Brutal Truth

The negative run worked, but it cannot answer the question Phase 11B actually needed answered: whether abandoned-object detection works on trusted positives. Spending a real 796.1-second CUDA run to end with zero usable positives is frustrating, but inventing labels or tuning against ambiguous clips would have been worse. The analyzer’s failure is honest, not a nuisance to suppress.

## Technical Details

The real DEIMv2 run completed 15/15 generic-negative clips and produced 443 canonical lifecycle rows. It emitted zero abandoned-object `START` records across 652.96 seconds, yielding 0.000 false alarms/hour. Provenance in `artifacts/phase11b_final/production-roi-run-v3.json` binds clip completion, ROI, prediction, dataset, event-rule, and inference-script hashes. `focused-tests-v4.xml` records 12/12 passing focused tests.

The final analyzer intentionally exited `2` with `ROI_POLICY_UNRESOLVED`. Precision, recall, F1, delay, duplicate rate, and first-failing-stage distribution remain non-computable because trusted positives equal zero.

## What We Tried

- Restored the test environment dependencies, then reran in-scope CV regression: 159 passed, 1 skipped.
- Ran the repository suite: 366 passed, 1 skipped, eight subtests passed; ten pre-existing/out-of-scope assessment-policy and web-demo failures remain.
- Preserved the frozen ROI and validated the full negative set instead of laundering diagnostic settings into production policy.

## Root Cause Analysis

The blocker is not inference execution or coordinate restoration. We reached the final gate without authoritative human/product labels for the four positive candidates. That makes positive ROI policy unverifiable. The environment also needed dependency restoration before regression evidence was trustworthy; leaving that drift unresolved would have made the validation claim bogus.

## Lessons Learned

Do not schedule tuning before positive adjudication is complete. Negative safety can prove absence of false alarms on the sampled clips; it cannot prove recall. A nonzero policy-gate exit must remain nonzero when evidence is missing.

## Next Steps

- Human/product owner: adjudicate the four candidates before any targeted fix or threshold change; timing TBD by owner.
- CV owner: keep Phase 11B frozen and do not start Phase 12 until trusted positives exist.
- Repository maintainers: separately resolve the ten out-of-scope suite failures and legacy `CVWorker.abandoned_engine` compatibility failure.

## Final Status

`ROI_POLICY_UNRESOLVED`; no targeted fix and no Phase 12.
