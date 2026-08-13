# Test Report — 2026-08-11 — DEIMv2 cycle-4 final gate

---
scope: deimv2-cycle-4-final-gate
status: passed-with-nonblocking-coverage-gap
---

## Summary

- Diff-aware mode analyzed 26 changed/untracked paths; config, dependency, Docker, and test-helper changes escalated to full suite.
- Final runtime gate: PASS. No production blocker reproduced.

## Test Results Overview

- Compile: PASS, CPython 3.11.9 `compileall -q app tests`, 0.170s.
- Targeted detector/tracker/runner/worker: 25 passed, 0 failed/skipped, 0.82s.
- Modified legacy integrations: 6 passed, 0 failed/skipped, 1.39s.
- Full `tests/`: 205 passed, 0 failed, 4 skipped, 8 subtests passed, 13.54s.
- Warnings: 3 full-suite deprecations; one Starlette/httpx, two trackers decorators.

## Coverage Metrics

- Unavailable: compatible local bundle lacks `coverage`/`pytest-cov`. No network install attempted.

## Runtime / Asset Smoke

- PASS: real Phase 7A checkpoint, DINOv3 backbone, CPU, 320x512 zero frame, no `PYTHONPATH`.
- SHA-256 checkpoint: `56063D9767463AD4DB270BA34CB82F86469D56FCB323E44B22C018898CB29BF3`; pinned value matches.
- SHA-256 backbone: `2053B865F4E2673FBA3F95F7E7E54AD5EE18143885E3AD27EAABB5B3B9919738`; pinned value matches.
- Load 8.043s; inference 559.147ms; 1 finite detection; class `luggage`.
- Scoped DEIM import works after Docker `PYTHONPATH` removal.
- Non-blocking warning: upstream DINO backbone loader uses `torch.load(weights_only=False)`; artifact hash verified before loader invocation.

## Diff / Residue Audit

- `git diff --check`: PASS; LF-to-CRLF working-copy warnings only.
- Production/config/requirements/Docker scan: 0 YOLO/Ultralytics matches.
- `back-end/` changed: 0. `front-end/` changed: 0.
- `.qa-tmp/` ignored; pytest basetemps only. No production edits by QA.

## Critical Issues

- None.

## Recommendations

1. Add compatible coverage tooling to standard QA image; enforce line/branch thresholds.
2. Track upstream Starlette/httpx, trackers, and Torch deserialization warnings.

## Unresolved Questions

- None.

**Status:** DONE_WITH_CONCERNS
**Summary:** Cycle-4 final gate green: targeted 25/25, legacy 6/6, full 205 passed + 8 subtests, real CPU asset smoke passed without `PYTHONPATH`.
**Concerns/Blockers:** Coverage unavailable; deprecation/security warnings non-blocking. No production blocker.
