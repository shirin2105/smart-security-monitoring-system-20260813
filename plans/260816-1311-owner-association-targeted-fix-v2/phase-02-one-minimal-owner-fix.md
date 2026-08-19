---
phase: 2
title: "One minimal owner fix"
status: completed
priority: P1
effort: 2h
dependencies: [1]
---

# Phase 2: One minimal owner fix

## Context Links

- Owner scoring/selection: `kaggle_pipeline/phase7c_kernel/phase7c_core.py:479-610`
- Event gate and owner-visible debounce: `kaggle_pipeline/phase7c_kernel/phase7c_core.py:692-746`
- Existing synthetic owner flows: `tests/unit/test_phase7c_v1_core.py:53-114`
- Owner-return adapter regression: `tests/unit/test_phase7c_production_adapter.py:27-43`

## Overview

Implement one evidence-selected class only: normalization defect, timing/window defect, bounded pre-stationary memory, local short-gap continuity without Re-ID, or threshold correction with separation proof.

## Requirements and data flow

Input track history stays per inference/camera call → one bounded owner transformation → deterministic candidate ranking → existing `OwnerAssociation` → unchanged last-visible debounce/event lifecycle. No cross-camera/process cache. Preserve: one owner per luggage; unresolved owner ≠ offscreen; visible owner blocks; return/pickup ends or blocks; reconnect/reset clears state.

## Related Code Files / ownership

- Modify: `kaggle_pipeline/phase7c_kernel/phase7c_core.py` only for production behavior.
- Modify: `tests/unit/test_phase7c_v1_core.py`; `tests/unit/test_phase7c_production_adapter.py` only if lifecycle coverage belongs there.
- Do not touch ROI, detector, ByteTrack, stationary, Crowd, Intrusion, Phase12, or configs unless evidence specifically selects threshold class E.

## Tests Before

1. Add failing reproduction for measured positive defect.
2. Add failing safety matrix: random passerby rejected; deterministic multi-person choice; owner visible far blocks; exit starts after debounce; return before debounce no START; return after START END; pickup before START no event; pickup after START END; reset/outage clears; no cross-camera contamination.
3. Add fragmentation and bounded-pruning tests only if that fix class is selected.

## Refactor / Tests After

4. Implement smallest single-class fix. Do not combine fallback classes or lower threshold first.
5. Run targeted owner/core/adapter tests, compile, then full `tests/unit`.
6. Reject immediately if passerby selection, owner-visible, return, pickup, reset, or isolation invariant fails.

## Test matrix and success criteria

| Level | Coverage |
|---|---|
| Unit | scorer components, reproduction, deterministic selection, lifecycle edge cases, trace neutrality |
| Integration | Phase7C adapter START/END and camera/reset isolation |
| E2E | deferred to Phase 3 real videos |

- [ ] One and only one behavior class changed; test fails before and passes after.
- [ ] No unbounded history/state; no changed public event contract.
- [ ] Full unit suite passes before CUDA spend.

## Work performed and outcome

- [x] One Class A scoring-normalization delta attempted; threshold and frozen subsystems unchanged.
- [x] Positive evidence changed scores: `LeftBag` `0.1957→0.7850`; `LeftBag_AtChair` `0.2417→0.7818`.
- [x] Rejected delta preserved in `artifacts/owner-association-v2/attempted-fix.patch`.
- [x] Production scoring delta rolled back after 2 negative false-positive STARTs.

No behavior fix accepted. Success criteria remain unchecked: second positive failed, negative safety failed, full unit suite not green.

## Risk Assessment / rollback / security

| Risk | L×I | Mitigation |
|---|---|---|
| Correct positives by selecting passersby | M×High | negative/multi-person tests; reject on frequent wrong-owner evidence |
| Shared state leaks cameras/reconnects | Low×High | avoid new shared state; instantiation/lifetime re-grep; reset/isolation tests |
| Compound fix hides root cause | M×High | one fix class and one focused commit/diff |

Rollback only this phase's production delta; diagnostics remain. Security impact low; traces stay local and bounded.

## Next Steps

Phase 3 starts only after targeted + full unit gates. Unresolved questions: chosen class remains evidence-controlled.
