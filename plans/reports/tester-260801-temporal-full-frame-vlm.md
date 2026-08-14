---
role: tester
date: 2026-08-01
scope: temporal-full-frame-vlm
status: pass-with-environment-limitations
---

# Test Report — 2026-08-01 — Temporal full-frame VLM

## Summary

Focused implementation valid. Added one test-only regression for exact inclusive 17-frame engine boundary and simultaneous-region call isolation. No implementation files edited.

## Diff-aware Scope

- Git baseline unavailable: repository has no `HEAD`; all files untracked.
- Scope derived from `plans/260801-temporal-full-frame-vlm-validation` ownership.
- Changed/inspected: `app/vlm/region_validator.py`, `app/events/abandoned_object.py`, `app/cv/worker.py`, `configs/event_rules.yaml`, `scripts/generate_static_abandoned_demo.py`.
- Mapped: five planned unit/integration files plus added `tests/unit/test_temporal_full_frame_boundaries.py`.
- Unmapped implementation files: none.

## Test Results Overview

- Plan-focused matrix: 23 passed, 0 failed, 0 skipped; 0.40s.
- Focused matrix plus added boundary test: 22 passed, 0 failed, 0 skipped; 0.33s.
- Critical timing/state subset repeated 5x: 40 passed total; 0 failures; 0.30–0.39s/run.
- Full suite: collection interrupted; 4 dependency errors, no tests executed.

## Contract Verification

| Requirement | Result | Evidence |
|---|---|---|
| No validation before `T+8` | PASS | unit timing assertions; repeated 5x |
| Inclusive ordered `[T-8,T+8]`, <=17 | PASS | added exact 17-frame engine regression; temporal adapter 17-image test |
| Full-scene frames | PASS | integration shape 24x32 and added pixel identity sequence |
| `detectedAt` remains `T` | PASS | accepted/unavailable and boundary assertions; candidate ID/lastSeenAt assertions |
| accept/unavailable emit; reject suppress | PASS | parametrized unit test |
| One call per region | PASS | simultaneous two-region regression; one call each |
| Bounded cleanup | PASS | buffer hard bound <=18; pending removed on missing-image completion; metadata cap 128 inspected |
| Temporal-disabled crop path unchanged | PASS | legacy cached crop-validator test; focused suite |
| Demo `stationary_seconds=6` | PASS | static inspection of `DEFAULT_CONFIG` |
| No token persisted | PASS | scoped secret-pattern scan: zero matches; config/demo expose no token option |

## Compile / Build Status

- `python -m compileall -q` on implementation, demo, and added test: PASS, no output.
- No production package build required for Python source-only change.
- Warning: source files `app/vlm/region_validator.py` (216 lines) and `app/events/abandoned_object.py` (448 lines) exceed repository 200-line convention; observational, not correctness blocker.

## Full-suite Collection Failures

- `scripts/test_finetuned_yolo26m.py`, `scripts/test_model_weights.py`, `scripts/test_yolo26m.py`: `ModuleNotFoundError: ultralytics`.
- `tests/test_agents/test_graph.py`: `ModuleNotFoundError: langgraph`.
- Pre-existing environment/dependency collection failures; unrelated to temporal implementation.
- Warnings: Starlette/httpx deprecation; three unknown `pytest.mark.asyncio` warnings.

## Coverage Metrics

- Line/branch/function percentages unavailable: `pytest-cov` absent; pytest rejects `--cov` arguments.
- Behavioral coverage strong for requested invariants. Remaining notable gap: explicit engine reset/end-of-stream API does not exist, so teardown cleanup cannot be invoked/tested directly.

## Performance / Determinism

- Slowest focused test: worker integration, 0.02s.
- Five repeated critical runs stable. No flaky behavior observed.

## Critical Issues

- None in scoped implementation.
- Full-suite quality gate blocked by missing declared runtime dependencies in provided vendored environment.

## Recommendations

1. High: install full `requirements.txt` environment; rerun full pytest.
2. Medium: add `pytest-cov`; capture line/branch/function metrics against 80/70/80 thresholds.
3. Medium: define engine `reset`/end-of-stream cleanup contract if long-lived worker reuse is planned; test buffer/pending release.
4. Low: configure `pytest-asyncio` marker/plugin; resolve Starlette/httpx warning.

## Exact Commands

```powershell
$env:PYTHONPATH="$PWD;$PWD\.runtime-packages;$PWD\.python-packages"
.\.runtime-packages\bin\pytest.exe tests/unit/test_region_validator.py tests/unit/test_abandoned_object.py tests/integration/test_static_abandoned_pipeline.py tests/integration/test_phase4_integration.py tests/integration/test_temporal_full_frame_vlm_pipeline.py -q --durations=10
.\.runtime-packages\bin\pytest.exe tests/unit/test_temporal_full_frame_boundaries.py tests/unit/test_region_validator.py tests/unit/test_abandoned_object.py tests/integration/test_temporal_full_frame_vlm_pipeline.py -q --durations=10
1..5 | ForEach-Object { .\.runtime-packages\bin\pytest.exe tests/unit/test_temporal_full_frame_boundaries.py tests/unit/test_abandoned_object.py -q }
.\.runtime-packages\bin\pytest.exe -q --durations=10
C:\Users\trand\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m compileall -q app\vlm\region_validator.py app\events\abandoned_object.py app\cv\worker.py scripts\generate_static_abandoned_demo.py tests\unit\test_temporal_full_frame_boundaries.py
```

## Unresolved Questions

- Should engine teardown/reset explicitly discard incomplete pending windows, or is instance destruction the intended policy?
