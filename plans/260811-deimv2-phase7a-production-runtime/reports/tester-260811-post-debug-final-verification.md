# Test Report — 2026-08-11 — DEIMv2 post-debug final verification

## Summary

- Diff-aware mode analyzed 26 changed/untracked paths; config/dependency changes escalated to full suite.
- Final gate: PASS. No production blocker reproduced.

## Test Results Overview

- Compile: PASS, `app` + `tests` via Python 3.11 `compileall`.
- Diff integrity: PASS, `git diff --check`; LF-to-CRLF working-copy warnings only.
- Targeted detector/tracker/runner/worker: 16 passed, 0 failed/skipped, 0.59s.
- Modified legacy integrations: 6 passed, 0 failed/skipped, 1.44s.
- Full `tests/`: 196 passed, 0 failed, 4 skipped, 8 subtests passed, 40.51s.
- Full-suite warnings: 3 (Starlette/httpx deprecation; two trackers decorator deprecations).

## Coverage Metrics

- Unavailable: no compatible locally cached `coverage`/`pytest-cov`. No network install attempted.

## Runtime / Performance

- Real asset CPU smoke: PASS on 320x512 frame.
- Model load: 8.170s. Inference: 555.736ms. Output: 1 finite detection, allowed class `luggage`.
- First smoke attempt failed only because QA harness omitted required `FrameData` rate/source fields; corrected rerun passed. Production code unaffected.

## Dependency Smoke

- torch 2.5.1+cu121; torchvision 0.20.1+cu121; Pillow 12.2.0.
- supervision 0.30.0; trackers 2.5.0.post0.
- pytest 9.1.1; cached LangGraph 1.2.10; LangChain 1.3.14; Pydantic 2.13.4.
- Declared CV pins match package versions; CUDA local-build suffix expected.

## Diff / Residue Audit

- Production/config/requirements/Docker scan: zero `YOLO` or `ultralytics` matches.
- `back-end/` changed files: 0. `front-end/` changed files: 0.
- Temporary `.qa-tmp/` created for isolated pytest and smoke assets. Cleanup command blocked by execution policy; non-production, untracked residue remains.

## Critical Issues

- None.

## Recommendations

1. Add compatible coverage tooling to standard QA image; enforce line/branch thresholds.
2. Remove `.qa-tmp/` before commit if still present.
3. Track upstream Starlette/httpx and trackers deprecations; non-blocking now.

## Unresolved Questions

- None.

**Status:** DONE_WITH_CONCERNS
**Summary:** Post-debug verification green: targeted 16/16, legacy 6/6, full suite 196 passed + 8 subtests, real asset CPU smoke passed.
**Concerns/Blockers:** Coverage unavailable; temporary `.qa-tmp/` cleanup blocked by policy. No production blocker.
