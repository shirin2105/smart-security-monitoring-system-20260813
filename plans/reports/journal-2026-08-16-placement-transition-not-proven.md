# Placement Transition Was Not Proven

**Date**: 2026-08-16 16:15
**Severity**: High
**Component**: Phase7C abandoned-object owner association
**Status**: Resolved — stopped without behavior change

## What Happened

We switched evidence from the rejected `phase8_dataset` to content-reviewed `tests/clips`. The real CUDA baseline scored 9 clips: all three reviewed positives (`aban3`, `cut`, `pets2006_3`) missed `ABANDONED_OBJECT START`, while all six negatives stayed at zero false positives. We then added a trace-only placement-transition hypothesis and reran `cut`, `pets2006_3`, and the negative risk clip `store-aisle-detection`.

## The Brutal Truth

The hypothesis sounded better than another proximity tweak, but the camera pipeline does not preserve the evidence it needs. That is frustrating: the feature logic can be clean and unit-testable while still being useless on real tracks. Shipping it anyway would have been tuning by wishful thinking.

## Technical Details

The frozen predicate required pre-placement bag motion `>= 0.25` person-diagonal, aligned-motion ratio `>= 0.60` with cosine `>= 0.5`, and relative-offset P90 spread `<= 0.35`. Real best bag-motion values were only `0.0261` for `cut`, `0.0392` for `pets2006_3`, and `0.0087` for `store-aisle-detection`. Sufficient diagnostic rows were 40, 22, and 508 respectively; predicate passes were `0/40`, `0/22`, and `0/508`. Event equivalence remained zero abandoned STARTs on all three clips.

## What We Tried

We rejected score/proximity-only relaxation because baseline positives and `store-aisle-detection` shared a best eligible owner score of `0.3167`. We instead instrumented synchronized person/luggage history and kept every new value trace-only. We rejected post-outcome threshold tuning because these same clips cannot be both calibration data and proof.

## Root Cause Analysis

Owner-association history begins after the luggage detector/tracker sees the object already nearly stationary. The moving-with-owner segment is absent, so the placement transition is unobservable. The failure is an evidence-boundary flaw, not a bad numeric threshold.

## Lessons Learned

Do not authorize behavior from synthetic separation alone. First prove the runtime records the causal interval the feature claims to measure.

## Next Steps

The CV owner-association owner must design a new observable-history strategy or separately reviewed calibration/holdout set before the next behavior proposal. Until then, keep production selection, score, ranking, threshold, stationary logic, and lifecycle unchanged. No open questions.
