---
title: "Evidence-Gated Placement-Transition Owner Association"
description: "Prove a synchronized-history placement feature before permitting one minimal owner-association behavior change."
status: completed_no_behavior_change
priority: P1
effort: 12h
branch: develop
tags: [bugfix, computer-vision, owner-association, tdd, critical]
blockedBy: []
blocks: []
created: 2026-08-16
---

# Evidence-Gated Placement-Transition Owner Association

## Overview

Replace the rejected closest-approach idea with a placement-transition hypothesis: genuine owner and bag co-move before the bag transitions to stationary while relative offset stays coherent. Add behavior-neutral features and TDD discriminators, then require real trace separation using only `tests/clips`. Permit exactly one minimal behavior delta only after proof; otherwise stop unchanged.

## Frozen Boundaries

- No threshold/config, detector, tracker, ROI, stationary, owner-visible/return/pickup, Intrusion, Crowd, or Phase12 change.
- `phase8_dataset` is excluded from calibration, acceptance, and safety decisions because the user rejected its real-world quality. Historical Phase 8 artifacts are context only.
- Real-video evidence comes only from `tests/clips`; labels must be content-reviewed or already explicitly adjudicated, never inferred from filenames.
- Preserve `OwnerAssociation` and public event contracts (`kaggle_pipeline/phase7c_kernel/phase7c_core.py:104`; `app/cv/contracts/cv_event.py:10`).
- Prior normalization delta remains rejected/rolled back after two WalkBy STARTs (`plans/260816-1311-owner-association-targeted-fix-v2/plan.md:35`).

## Verified Data Flow

Track observations → per-camera bounded history ≥30 s (`app/cv/events/phase7c_abandoned_adapter.py:47,65`) → grouping/quality/stitch/stationary → sole `associate_owner` call (`kaggle_pipeline/phase7c_kernel/phase7c_core.py:666,734`) → synchronized rows through stationary start (`:481-516`) → candidate selection → last-visible/away gate (`:623-647,747-759`) → adapter owner-visible/pickup suppression (`app/cv/events/phase7c_abandoned_adapter.py:88-91`) → lifecycle events (`app/cv/event_manager.py:53`).

## Phases

| # | Phase | Depends | Status |
|---|---|---|---|
| 1 | [Feature contract and TDD discriminators](./phase-01-start.md) | — | Completed |
| 2 | [Real trace separation gate](./phase-02-real-trace-separation-gate.md) | 1 | Completed — not proven |
| 3 | [One minimal evidence-gated behavior change](./phase-03-one-minimal-evidence-gated-behavior-change.md) | 2 proof | Not authorized |
| 4 | [Acceptance, regression, and rollback](./phase-04-acceptance-regression-and-rollback.md) | 3 | Not applicable |

Graph: `P1 → P2 → {no proof: STOP | proof: P3 → P4}`. No parallel production edits; ownership transfers sequentially.

## Success Criteria

- [x] Synthetic tests distinguish placement from passerby, crossing, sparse/fragmented, already-stationary, and picked-up.
- [ ] Fresh `tests/clips` traces prove the frozen Phase 1 predicate separates reviewed abandoned positives from reviewed non-abandoned risk candidates.
- [ ] AtChair association and owner-visible/ID-continuity outcomes reported independently.
- [ ] At most one behavior delta; every reviewed positive STARTs; every reviewed negative remains zero; regressions green.
- [x] Failed proof/gate leaves no behavior change.

## Terminal Outcome

- Phase 1: complete; behavior-neutral diagnostics and synthetic discriminators delivered.
- Phase 2: `PLACEMENT_TRANSITION_NOT_PROVEN`; terminal run covered two reviewed positives and one reviewed negative, not the full reviewed manifest. Frozen predicate passed 0 candidates; product proof and downstream acceptance not met.
- Phase 3: unauthorized by failed Phase 2 proof gate; no behavior delta applied.
- Phase 4: not applicable because Phase 3 did not run.
- Scope change: stopped after failed proof as preregistered; Phase 3/4 execution removed from active scope. Delivery impact: no owner-association product fix accepted.
- Open blocker: current synchronized luggage history begins after apparent placement motion. Owner: implementation lead. Unblock only with new product-authorized calibration/holdout design; do not tune against this run.

## Compatibility / Rollback

No migration. Diagnostic fields stay trace-only; public users/integrations unchanged. Roll back Phase 3’s one hunk only, retain tests/evidence, rerun event-equivalence and targeted suites.

## Review and Validation Log

- Review lenses: assumption, failure-mode, scope/complexity. Findings accepted into plan: robust gap handling; preregistration/post-hoc rerun rule; AtChair downstream feasibility stop; exact-hunk rollback. Rejected: threshold tuning and ID-continuity repair because user froze them.
- Verification tier: Standard (Fact Checker + Contract Verifier). Claims checked: 31; verified: 31; failed: 0; unverified: 0.
- Caller trace: `associate_owner` definition/call count = 1/1 (`kaggle_pipeline/phase7c_kernel/phase7c_core.py:472,734`). Adapter lifetime is per worker/camera (`app/cv/worker.py:99`) with bounded rows (`app/cv/events/phase7c_abandoned_adapter.py:47,65`).
- Contract trace: `OwnerAssociation` remains internal shape at `phase7c_core.py:104-118`; external `CVEvent` remains at `app/cv/contracts/cv_event.py:10`; lifecycle START meaning remains `app/evaluation/phase11_schema.py:133`.
- Whole-plan consistency sweep: 5 files reread; 4 decision deltas reconciled; 0 stale references; 0 unresolved contradictions.
- CLI format validation: passed on 2026-08-16.

## Preregistered Predicate

Before fresh outcomes are opened, freeze: final synchronized segment ending at stationary start; duplicate/non-finite timestamps invalidate evidence; gap >0.5 s truncates; at least 4 samples/3 intervals and 0.6 s support; pre-placement bag motion >=0.25 person-diagonal; >=60% moving intervals aligned with cosine >=0.5; relative-offset P90 spread <=0.35 person-diagonal. Missing/sparse evidence fails closed. Fresh outcomes may reject this predicate but may not tune it.

## Unresolved Questions

- Will product authorize a new calibration/holdout design for placement evidence, or close this hypothesis?

<!-- slug: evidence-gated-placement-transition-owner-association -->
