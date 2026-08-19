---
phase: 2
title: "Real trace separation gate"
status: completed_not_proven
priority: P1
effort: 4h
dependencies: [1]
---

# Phase 2: Real trace separation gate

## Context Links

- Runner: `scripts/phase11_infer.py:60-67,95-160`
- Adapter history/core call: `app/cv/events/phase7c_abandoned_adapter.py:47,65-68`
- Trace builder: `app/cv/events/phase7c_owner_association_trace.py:18-61`
- Prior WalkBy rejection: `plans/260816-1311-owner-association-targeted-fix-v2/phase-03-cuda-validation-and-final-status.md:65-69`

## Overview / Requirements

Run fresh trace-only diagnostics before behavior edits using only videos under `tests/clips`. Use the frozen content-review manifest `evaluation/placement-transition-test-clips.json`: positives are `aban3.mp4`, `cut.mp4`, and `pets2006_3.mp4`; six reviewed clips are negative; `walking_people_browser.webm` is excluded as duplicate content. Freeze model/checkpoint, inference profile, tracker, sampling, ROI, stationary, thresholds; no between-clip tuning. Record command, source/diff hash, CUDA/device, clip/config/checkpoint hashes, feature schema, candidates, lifecycle counts. Do not read or run `phase8_dataset` inputs.

## Architecture / Proof Rule

Real `tests/clips` video → unchanged runtime → synchronized candidate features → immutable versioned JSONL/CSV → separation report. Use only the exact frozen predicate in `plan.md`; no outcome-driven cutoff changes. Proof requires every reviewed positive owner candidate pass and every reviewed negative alert-risk candidate fail. Frame removal is sensitivity analysis only, not independent generalization evidence. Any formula adjustment invalidates this gate and requires new isolated holdout evidence.

Every reviewed positive has two independent gates:

1. Correct owner passes association/selection.
2. Require: correct owner selected; `owner_last_visible_s` present; `candidate_time=max(stationary_confirmed_s, owner_last_visible_s + frozen away_hold_s)`; `candidate_time <= stationary_run.end_s`; adapter owner is not visible at candidate time. Failure yields `POSITIVE_DOWNSTREAM_BLOCKED`; Phase 3 cannot run.

## Files / Ownership

| Action | File | Purpose |
|---|---|---|
| Create | `scripts/placement_transition_analyze.py` | schema-validated offline analysis only |
| Modify if needed | `scripts/phase11_infer.py` | trace plumbing only |
| Create | `reports/placement-separation-report.md` under this plan | proof record |
| Create | isolated `artifacts/` run directory | provenance/traces |

No production selection ownership.

## Steps / Evidence Matrix

1. Inventory and content-review `tests/clips`; freeze adjudication, preregistered rules, and baseline event counts before scored runs.
2. Run every reviewed clip; list every candidate, not only best: support/gaps, velocities, cosine, speed agreement, offset drift/spread, transition, selected ID, rejection, START.
3. Validate exact clip set, reject duplicates/non-finite/mixed schemas, run sensitivity, and hash immutable outputs.
4. Branch: `PROVEN` authorizes Phase 3; `PLACEMENT_TRANSITION_NOT_PROVEN` stops unchanged; `POSITIVE_DOWNSTREAM_BLOCKED` stops because acceptance needs forbidden semantics.

| Clip | Required evidence |
|---|---|
| `pets2006_3.mp4` | reviewed unattended-bag interval; true owner passes; downstream feasible |
| `aban3.mp4` | reviewed unattended-bag interval; true owner passes; downstream feasible |
| Reviewed negatives in `tests/clips` | zero START baseline; risky candidates fail predicate |
| Ambiguous clips | excluded with reason; never silently counted positive/negative |

## Success Criteria

- [ ] Complete fresh reviewed `tests/clips` candidate table and provenance.
- [ ] One preregistered rule has strict robust separation.
- [ ] Trace-only lifecycle counts equal baseline.
- [ ] Association vs owner-visible/ID continuity explicit for each reviewed positive.
- [ ] No proof means no production edit.

Terminal result: `PLACEMENT_TRANSITION_NOT_PROVEN`. Only `cut.mp4`, `pets2006_3.mp4`, and `store-aisle-detection.mp4` completed in the terminal run; full reviewed manifest, strict separation, lifecycle equivalence, and per-positive downstream diagnosis were not proven. Product acceptance criteria remain unchecked. Phase 3 therefore unauthorized.

## Risks / Rollback

| Risk | L×I | Mitigation |
|---|---|---|
| Small reviewed-set overfit | High×High | physical conjunctive evidence; run every independent reviewed `tests/clips` video |
| Wrong labels | M×High | trusted evidence; enumerate all candidates |
| Trace changes runtime | Low×High | hashes + event equivalence |
| AtChair infeasible | M×High | independent gate and mandatory stop |

Retain evidence; revert trace plumbing if normalized events differ. No external upload.

## Unresolved Questions

- Whether product will authorize a new calibration/holdout design; current run cannot be reused for threshold tuning.
