---
date: 2026-08-10
session: phase8-cv-e2e-validation-gates
---

# Phase 8 CV E2E Validation: Tooling Ready, Evidence Missing

**Date**: 2026-08-10 11:25  
**Severity**: High  
**Component**: CV event validation  
**Status**: Blocked

## What Happened

We froze the Phase 7A DEIMv2 checkpoint, class-wise ByteTrack runtime, and current Phase 7C abandoned-object reasoning. Phase 8 added a thin `inference_video.py` adapter, one JSONL contract for `ZONE_INTRUSION`, `CROWD_THRESHOLD`, and `ABANDONED_OBJECT`, event matching, delay and false-rate metrics, and an attribution row for every FP/FN. Focused tests passed 19/19. A real local replay produced 11 schema-valid predictions: ten intrusion events and one abandoned-object candidate; crowd never reached its configured threshold.

## The Brutal Truth

The tooling works, but the requested validation does not exist yet. Calling this phase complete would be dishonest. The account exposes only the single-video Phase 7B ABODA dataset, not the required 20–30 labeled positive/negative clips. That means Kaggle cannot start a legitimate batch, and precision/recall claims would be manufactured from an inadequate smoke clip. It is frustrating to have the machinery ready while the actual evidence gate is still empty, but inventing a benchmark would be worse.

## Technical Details

The supplied evaluator had correctness traps. It could accept a prediction before `trigger_time_s` as a TP, count an `ABANDONED_OBJECT_CANDIDATE` false prediction as a false alarm, and let a partial `--continue-on-error` batch produce merged output without a hard final failure. The Kaggle command template also needed nested tracker placeholders preserved instead of formatting them too early. Tests now lock these behaviors, including candidate-only `false_candidates_per_hour`, alert-only `false_alarms_per_hour`, duplicate identity rejection, and fail-closed batch coverage.

## Decision and Root Cause

We rejected retraining, S4, EdgeCrafter, threshold tuning, and architecture changes. None is justified before error attribution. The blocker is not model quality; it is missing labeled external input and a Kaggle dataset slug. Candidate output remains explicitly separate from confirmed alerts, preventing a dangerous capability claim.

## Lessons Learned

An evaluator can lie while producing plausible numbers. Trigger boundaries, partial-batch handling, and candidate-versus-alert semantics need tests before any metric is trusted.

## Next Steps

- Dataset owner: provide the Kaggle slug for 20–30 labeled clips and ground-truth JSONL.
- CV owner: launch the frozen batch once attached, then review every `UNKNOWN` FP/FN attribution before changing any component.

