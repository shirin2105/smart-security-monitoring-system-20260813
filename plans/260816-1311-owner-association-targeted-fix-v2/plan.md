---
title: "Owner Association Targeted Fix v2"
description: "Evidence-gated TDD plan for one minimal owner-association fix and full CUDA safety validation."
status: completed
priority: P1
effort: 8h
branch: model-CV-v1
tags: [bugfix, computer-vision, owner-association, tdd]
blockedBy: []
blocks: []
created: 2026-08-16
---

# Owner Association Targeted Fix v2

## Overview

Finish only the owner-association remainder after Product Policy v2. First prove the positive failure from fresh traces; then select and implement exactly one bounded fix; finally run ordered real-CUDA and regression gates. No ROI, detector, tracker, stationary, Intrusion, Crowd, Phase 12, or unrelated Product Policy changes.

## Verified baseline

- Owner threshold `0.60`, near norm `0.50`, overlap minimum `0.70 s`: `kaggle_pipeline/phase7c_kernel/phase7c_core.py:52-57`.
- Scorer is `0.65*inside + 0.25*near + 0.10*overlap`: `kaggle_pipeline/phase7c_kernel/phase7c_core.py:515-543`; rejection at threshold: `:545-572`.
- Association uses luggage history only through stationary-run start: `kaggle_pipeline/phase7c_kernel/phase7c_core.py:479-487`.
- Product Policy v2 uses full frame and owner last-visible debounce: `kaggle_pipeline/phase7c_kernel/phase7c_core.py:671-714`.
- Current traces expose candidate score/distance/age but not all requested derived fields: `artifacts/phase11b2/traces-after/LeftBag.jsonl:162`.
- Existing evidence mixes `CANDIDATE_SCORE_BELOW_THRESHOLD` and `NO_PERSON_WITHIN_DISTANCE`; root cause remains unproven: `artifacts/phase11b2/positive_roi_audit.csv:2-3`.
- Fifteen manifest negatives exist: `phase8_dataset/manifest.json:78-260`; prior no-ROI run reported 15/15 and zero START, not post-fix evidence: `artifacts/phase11b2/negative_safety.csv:2`.

## Data flow

Video → real DEIMv2/CUDA detections → ByteTrack rows → quality/stitch/stationary (frozen) → `associate_owner` diagnostics/evidence gate → one owner fix → owner last-visible debounce → adapter lifecycle events → metrics/status report. Trace mode may add evidence only; disabled/enabled outputs must be event-identical.

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | [Evidence gate and failing tests](./phase-01-evidence-gate-and-failing-tests.md) | Completed — evidence gate passed |
| 2 | [One minimal owner fix](./phase-02-one-minimal-owner-fix.md) | Completed — attempted, rejected, rolled back |
| 3 | [CUDA validation and final status](./phase-03-cuda-validation-and-final-status.md) | Completed — terminal rejection |

## Terminal outcome

`OWNER_FIX_REJECTED_FALSE_POSITIVES`

- Root cause proven: `SCORING_NORMALIZATION_DEFECT`; fresh CUDA scores `0.1957` and `0.2417` below `0.60`.
- One Class A scoring-normalization delta attempted. `LeftBag` reached 1 START; `LeftBag_AtChair` remained 0 START at `OWNER_AWAY_NOT_REACHED`.
- Trusted picked-up negative stayed 0 START. Generic negatives completed 15/15 but gained 2 STARTs on `WalkByShop1front`; mandatory rejection gate failed.
- Scoring delta rolled back. Diagnostic instrumentation retained. Stage E local clips not run after rejection gate.
- Tests: focused 15 passed; explicit CV regressions 83 passed; full unit 326 passed, 1 skipped, 8 failed. Product acceptance not achieved.

## Dependency and ownership

`P1 → P2 → P3`; no parallel edits. P1 owns diagnostics/harness + diagnostic tests. P2 owns scorer logic + behavior tests. P3 owns artifacts/report only. Existing dirty changes are user-owned; preserve and diff-review before touching overlapping files.

## Success Criteria

- [ ] Evidence table answers both trusted positives before behavior edit.
- [ ] Exactly one evidence-selected fix; all required tests green.
- [ ] CUDA order honored; positives each ≥1 START, picked-up negative 0 START, 15 negatives no unacceptable FP increase.
- [ ] Local clips inspected without filename-derived GT; regressions pass; exactly one required final status recorded.

Acceptance remains unchecked: terminal execution completed, product fix rejected.

## Scope changes and risks

- Stage E local inventory/inference skipped per early-stop gate after negative false positives. Impact: no local false-alert inspection metrics.
- Attempted behavior change reverted. Current production scorer remains baseline; no accepted owner-association improvement delivered.
- Provenance created retrospectively; run files hash-bound, but attempted-fix source identity absent at execution time. Exact rejected delta preserved in `artifacts/owner-association-v2/attempted-fix.patch`.
- Full-unit gate not green: 8 failures classified out-of-scope in handoff, but acceptance requires pass and remains unmet.

## Rollback

Revert only P2 owner-fix commit/config delta; retain P1 diagnostics/tests and P3 evidence. Re-run baseline targeted tests to prove Product Policy v2 remains intact.

## Unresolved questions

None. Terminal status fixed by observed false positives; further fix requires a new authorized plan and fresh baseline.

<!-- slug: owner-association-targeted-fix-v2 -->
