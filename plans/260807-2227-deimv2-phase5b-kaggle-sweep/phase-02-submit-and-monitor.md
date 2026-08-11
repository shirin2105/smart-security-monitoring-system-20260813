---
phase: 2
title: "Submit and monitor"
status: pending
priority: P1
effort: 20m operator time plus Kaggle runtime
dependencies: [1]
---

# Phase 2: Submit and Monitor

## Context Links

- [Package phase](phase-01-package-and-validate.md)
- Runtime entry/control flow: `C:/Users/trand/Downloads/Others/deimv2_phase5b_tiling_sweep.py:1207`

## Overview

Push one private Kaggle kernel version and monitor from the terminal until a terminal state. Never resubmit automatically: each retry requires evidence-based classification to avoid burning T4 quota.

## Requirements

- Push only the Phase 5B kernel directory with `kaggle kernels push -p <dir>`.
- Record returned kernel slug/version/timestamp and source hash.
- Poll `kaggle kernels status <owner/slug>` at a moderate interval, reporting state changes; stop on COMPLETE, ERROR, CANCELLED, or timeout.
- Keep one T4; do not start parallel/retry kernels.

## Architecture and Data Flow

Validated package -> Kaggle API push -> queued/running version -> status polls -> terminal state. Runtime flow is environment/dependencies -> pinned repo -> inputs/backbone -> taxonomy normalization -> model -> warmup -> eight sequential inference/evaluation jobs -> incremental summaries (`source:1214-1309`).

## Implementation Steps

1. Re-run hash/static gates immediately before push; capture push response.
2. Poll status without blocking user-visible updates longer than 60 seconds. Record UTC/local timestamps and elapsed time.
3. On COMPLETE, proceed once to Phase 3.
4. On ERROR/CANCELLED/timeout, capture status response and full kernel log/traceback through available Kaggle output/log surface. Report exception type, final traceback frames, last successful `[RESULT]`, and any partial summaries.
5. Classify failure: infrastructure/quota, dependency/network, missing/ambiguous input, GPU/OOM, baseline/taxonomy guard, or source runtime defect. Retry unchanged only for transient infrastructure failures. Any source fix requires a reproducible blocker, minimal diff, hash disclosure, user approval, and a new version.

## Test Matrix

| Level | Scenario | Expected evidence |
|---|---|---|
| Integration | push accepted | kernel slug/version returned |
| Integration | queued/running | monotonic status timeline |
| E2E success | COMPLETE | output retrieval available |
| E2E failure | ERROR | full traceback + last progress + partial files |
| Guardrail | accidental retry/parallel run | prevented without approval |

## Failure Modes and Risks

| Failure | L×I | Mitigation |
|---|---|---|
| T4 quota/queue delay | M×M | one run, status timeline, no speculative retry |
| pip/git/backbone download fails | M×H | internet enabled; preserve traceback; classify transient vs deterministic |
| ambiguous/missing checkpoint or annotation | L×H | exact two inputs; capture candidate lists from raised error (`source:278-320`) |
| CUDA OOM | M×H | no parallel kernels; retain experiment/progress line; no silent parameter change |
| partial experiment failure | M×M | script saves summaries after each completed result (`source:1289-1290`); download partial evidence |

## Rollback

Stop monitoring without changing remote data. If cancellation is necessary, cancel only this new version and retain its identifiers/log. Do not delete remote evidence until downloaded and explicitly approved.

## Success Criteria

- [ ] Exactly one new version pushed.
- [ ] Terminal state and timeline captured.
- [ ] COMPLETE proceeds to retrieval, or failure report includes full traceback and partial-result inventory.

## Next Steps

Phase 3 requires COMPLETE. Failed runs return to diagnosis, not automatic source editing.

## Unresolved Questions

None.
