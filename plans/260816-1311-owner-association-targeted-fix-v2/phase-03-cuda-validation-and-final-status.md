---
phase: 3
title: "CUDA validation and final status"
status: completed
priority: P1
effort: 4h
dependencies: [2]
---

# Phase 3: CUDA validation and final status

## Context Links

- Trusted/local clip harness and roles: `scripts/product_policy_v2_local_clip_eval.py:31-41,105-156`
- Local inventory/output flow: `scripts/product_policy_v2_local_clip_eval.py:161-292`
- Fifteen generic negatives: `phase8_dataset/manifest.json:78-260`
- Local clips include required `aban3`, `pets2006_3`, bottle/people/store/walking clips: `tests/clips/` (inventory must be regenerated at run time).
- Temporal suites: `tests/integration/test_temporal_worker_eos.py`, `tests/unit/test_phase10_runtime.py`, `tests/unit/test_phase10b_runtime.py`.

## Overview

Validate the one fix on real CUDA in strict order, then regressions and exact terminal status. No tuning between clips; any additional behavior edit returns to Phase 1 with a new baseline.

## Architecture / execution order

Real video → unchanged unified worker → new isolated artifact directory → lifecycle collapse/count → adjudication-aware metrics/report.

1. Record commit/diff, CUDA device, config, model/checkpoint checksum, clip manifest/checksums, trace flag.
2. CUDA A `LeftBag`; B `LeftBag_AtChair`. If either fails, if both fail stop immediately; report each new first failing stage. No opportunistic second fix.
3. C `LeftBag_PickedUp`: require 0 ABANDONED_OBJECT START.
4. D all 15 manifest-classified generic negatives: complete coverage, compare baseline FP, reject material increase.
5. E regenerate `tests/clips` inventory and run every local video. Explicitly include `aban3.mp4`, `pets2006_3.mp4`, `bottle-detection.mp4`, `people_detection.mp4`, `store-aisle-detection.mp4`, `walking_people.mp4`; run demo/ABODA if present. Treat unreviewed clips as false-alert inspection only—never infer GT from filename.
6. Run Intrusion, Crowd, Phase10 temporal, then full CV unit/integration/contract suites. Preserve current unrelated dirty files.

## Test matrix / measurable outputs

| Gate | Pass condition |
|---|---|
| Trusted positives | each ≥1 START; TP/FN/recall reported |
| Trusted negative | picked-up FP=0 |
| Generic negatives | 15/15 observed; FP and delta reported; no unacceptable increase |
| Local unreviewed | all inventoried; alert count + manual-inspection list, no claimed recall |
| Owner quality | success rate, before/after best scores, owner id, association delay |
| Lifecycle | duplicate rate; visible-far/return/pickup tests pass |
| Regressions | Intrusion PASS, Crowd PASS, Phase10 temporal PASS, full CV suites PASS |

Do not report official event delay from old GT trigger times. Association delay is allowed; event delay requires new owner-exit annotation.

## Final status and success criteria

Emit exactly one: `ABANDONED_READY_FOR_PHASE12`, `OWNER_FIX_PARTIAL`, `OWNER_FIX_REJECTED_FALSE_POSITIVES`, `OWNER_ROOT_CAUSE_NOT_PROVEN`, `NEED_BETTER_POSITIVE_DATA`. “Ready” does not authorize Phase12.

- [ ] Both positives pass, picked-up stays zero, negatives safe, all regressions pass for ready status.
- [ ] Partial status names remaining first failing stage; false-positive status includes offending clips/owners.
- [ ] Final report contains commands, manifests, metrics, artifact paths, failures, and no overstated GT claims.

## Validation performed

- [x] CUDA positives completed before/after: `LeftBag` 1 START; `LeftBag_AtChair` 0 START, first failing stage `OWNER_AWAY_NOT_REACHED`.
- [x] Trusted `LeftBag_PickedUp` negative completed with 0 START.
- [x] Generic negatives completed 15/15; 2 STARTs on `WalkByShop1front` triggered mandatory rejection.
- [x] Focused tests: 15 passed. Explicit Intrusion/Crowd/Phase10 temporal/Phase7C regressions: 83 passed.
- [x] Full unit suite recorded: 326 passed, 1 skipped, 8 failed.
- [x] Final artifact report emitted exactly `OWNER_FIX_REJECTED_FALSE_POSITIVES`.
- [x] Rejected scoring delta rolled back; diagnostics retained.

## Incomplete acceptance and scope deviation

- [ ] Both trusted positives pass: `LeftBag_AtChair` failed.
- [ ] Negative safety passes: 2 false-positive STARTs observed.
- [ ] Stage E local clips inventoried and inspected: intentionally stopped after mandatory stage D rejection.
- [ ] Full unit gate passes: 8 failures remain.

Terminal rejection is complete; successful product acceptance remains false.

## Risk Assessment / rollback / security

| Risk | L×I | Mitigation |
|---|---|---|
| CUDA nondeterminism/incomplete clip coverage | M×High | fixed config/checksums, strict manifest, rerun same seed only |
| Long run hides early invalid fix | M×High | positives first; stop gate before negatives |
| Unreviewed filename treated as truth | M×High | alert-inspection classification only |

On rejection, revert Phase 2 behavior delta and rerun targeted baseline tests; keep artifacts immutable for audit. No external upload. Unresolved questions: none.
