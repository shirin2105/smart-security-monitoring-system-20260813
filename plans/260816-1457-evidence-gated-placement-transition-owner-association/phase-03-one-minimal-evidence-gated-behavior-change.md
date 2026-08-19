---
phase: 3
title: "One minimal evidence-gated behavior change"
status: unauthorized
priority: P1
effort: 2h
dependencies: [2]
---

# Phase 3: One minimal evidence-gated behavior change

Terminal disposition: not authorized. Phase 2 did not prove the preregistered predicate. No implementation or acceptance work may be claimed.

## Overview / Requirements

Conditional: execute only on Phase 2 `PROVEN` and feasible AtChair downstream path. Reuse Phase 1 features. Exactly one behavior delta: a quality/overlap-eligible candidate qualifies when the unchanged score reaches the unchanged threshold OR the frozen placement predicate passes. Existing association scores and ranking/tie behavior remain unchanged; among qualifying candidates, the existing score order selects the owner. Do not add a second gate, score change, closest approach, ID stitching, state/config/class, threshold, rejection-value, or lifecycle edit. Missing placement evidence gives no alternate qualification. Existing output fields/timestamps remain unchanged.

## Data Flow

Existing synchronized rows → frozen predicate → one alternate-qualification boolean → unchanged score ordering and `OwnerAssociation` → unchanged last-visible/away/adapter lifecycle.

## Files / Ownership

| Action | File | Purpose |
|---|---|---|
| Modify | `kaggle_pipeline/phase7c_kernel/phase7c_core.py` | one conditional behavior hunk |
| Modify | `tests/unit/test_phase7c_v1_core.py` | RED/GREEN safety matrix |
| Modify if assertion only | `tests/unit/test_phase7c_production_adapter.py` | frozen lifecycle checks |

Sequential ownership transfer; no configs/contracts touched.

## Tests Before / Steps

1. Verify exact Phase 2 rule/margin and AtChair feasibility.
2. Add RED: genuine placement selected; passerby, crossing, sparse/fragmented, already-stationary, picked-up rejected. Add deterministic two-person, trace equivalence, contract shape.
3. Apply one alternate-qualification conditional hunk; record GREEN.
4. Diff-audit thresholds/config/lifecycle untouched.
5. Run targeted core/adapter/contracts. Any failure → immediate exact-hunk rollback and `PLACEMENT_TRANSITION_REJECTED`.

## Test Matrix / Gate

- Unit: six scenarios, support/gaps, multi-person determinism, `OwnerAssociation` shape.
- Integration: selected owner currently visible blocks; return/pickup block/end; reset/camera isolation.
- Contract: event type/state/payload unchanged.
- Commands: compileall; `pytest -q tests/unit/test_phase7c_v1_core.py tests/unit/test_phase7c_production_adapter.py tests/unit/test_phase7c_event_contract.py tests/unit/test_cv_event_manager.py`.

## Success Criteria

- [ ] One proven predicate only; no numeric threshold change.
- [ ] Required behavior RED then GREEN.
- [ ] Negative/lifecycle/isolation/contract tests pass.

## Risks / Compatibility / Rollback

| Risk | L×I | Mitigation |
|---|---|---|
| Rejects stationary-from-first-frame | High×Medium | intentional fail-closed; explicit test |
| Hidden compound fix | M×High | one-hunk diff budget |
| AtChair still downstream-blocked | M×High | Phase 2 feasibility gate; no workaround |

No schema/data migration. Roll back one hunk and rerun baseline; diagnostics remain.

## Unresolved Questions

- Requires new product authorization after a separately approved calibration/holdout design.
