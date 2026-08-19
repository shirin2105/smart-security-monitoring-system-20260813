---
phase: 4
title: "Acceptance, regression, and rollback"
status: not_applicable
priority: P1
effort: 3h
dependencies: [3]
---

# Phase 4: Acceptance, regression, and rollback

Terminal disposition: not applicable. Phase 3 was not authorized and no behavior delta exists to accept or roll back. Success criteria remain unchecked because product acceptance did not run.

## Overview / Execution Order

Freeze source/config/model/clip hashes; no tuning. Run every content-reviewed video in `tests/clips`: each reviewed abandoned positive must emit START; every reviewed negative must emit zero START with no per-clip or aggregate increase; ambiguous clips remain excluded and reported. Then run Phase7C, Intrusion, Crowd, contract, Phase10 temporal, unit/integration regressions. `phase8_dataset` is forbidden as acceptance input. Any failure rolls back behavior. Only START counts as alert (`app/evaluation/phase11_schema.py:133,168-170`).

## Files / Ownership

| Action | File | Purpose |
|---|---|---|
| Create | plan-local final report | commands, hashes, counts, decision |
| Create | isolated artifact directory | events/traces/manifests |
| No edits | production/config source | frozen validation |

Phase 4 owns reports/artifacts only. Diagnostic and behavior rollback are independent: diagnostic code remains only if schema/neutrality/determinism gates pass; behavior rollback reverts the Phase 3 exact hunk on any acceptance failure.

## Test Matrix

| Gate | Pass | Failure action |
|---|---|---|
| Reviewed positives in `tests/clips` | each START ≥1 | rollback |
| Reviewed negatives in `tests/clips` | each START=0; no FP increase | rollback |
| Owner semantics | visible/return/pickup unchanged | rollback |
| Intrusion/Crowd | green | rollback |
| Temporal/contracts/full regressions | green | rollback |

## Steps / Success Criteria

1. Verify only authorized diff and targeted tests green.
2. Run the frozen reviewed `tests/clips` manifest; stop/rollback on first hard failure.
3. Complete all reviewed-negative comparisons, then all regression suites.
4. Distinguish pre-existing dirty baseline failures; never waive new failures.
5. Emit exactly one: `PLACEMENT_TRANSITION_ACCEPTED`, `PLACEMENT_TRANSITION_NOT_PROVEN`, or `PLACEMENT_TRANSITION_REJECTED`.
6. After rejection, rerun targeted baseline and event-equivalence checks.

- [ ] Every reviewed `tests/clips` positive STARTs.
- [ ] Every reviewed `tests/clips` negative completes with zero START and no FP increase.
- [ ] All named regressions green.
- [ ] Report includes provenance, counts, AtChair dual diagnosis, accepted/reverted diff state.
- [ ] Accepted state has exactly one behavior delta; rejected state none.

## Risks / Rollback

| Risk | L×I | Mitigation |
|---|---|---|
| GPU nondeterminism | M×High | frozen rerun; never tune |
| Dirty/failing baseline | High×High | pre-change baseline; no new failures |
| Partial run called accepted | M×High | 15/15 manifest + terminal rules |
| Rollback damages user work | M×High | revert exact Phase 3 hunk; no reset/checkout |

No migration or consumer change. Diagnostics retained; artifacts local/redacted if shared.

## Unresolved Questions

None.
