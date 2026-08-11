---
role: tester
date: 2026-08-01
scope: temporal-full-frame-vlm-resource-payload-eos-rerun
status: pass-with-environment-limitations
---

# Test Report — Temporal full-frame VLM rerun

## Summary

Expanded contract passes. Implementation files untouched. Added worker EOS/config integration test and strengthened endpoint-label assertions.

## Diff-aware Scope

- No Git `HEAD`; repository remains entirely untracked. Plan-owned files used as scope.
- Implementation: validator, abandoned-object engine, worker, event config, demo.
- Tests: validator, abandoned engine, exact temporal boundaries, static pipeline, worker integration, temporal pipeline, worker EOS.

## Test Results Overview

- Expanded focused matrix: 32 passed, 0 failed, 0 skipped; 1.08s.
- Endpoint/resource/EOS confirmation: 19 passed; 1.00s.
- Resource/payload/finalization subset repeated 3x: 12 passed total; 0 failures; 0.41–0.53s/run.
- Full suite: 4 collection errors before execution; unrelated missing dependencies.

## Verification Matrix

| Requirement | Result | Evidence |
|---|---|---|
| No validation before `T+8` | PASS | parametrized engine timing test; exact boundary test |
| Ordered inclusive `[T-8,T+8]`, <=17 | PASS | exact 17 timestamps and pixel sequence |
| Endpoint preservation | PASS | engine retains first/last samples; payload labels `-8.000s`, `+8.000s` |
| Event-nearest compatibility selection | PASS | old-validator bridge test |
| Full-scene proportional max dimension | PASS | 4K `2160x3840` becomes `270x480`; source dimensions retained |
| Buffer <=12 MB | PASS | production ceiling asserted `12,000,000`; stronger 3 MB runtime test passes |
| Aggregate serialized request budget | PASS | serialized payload measured <=500,000 bytes |
| Oversize no-network | PASS | 64 KB cap returns `request_too_large`; client raises if called |
| Offset + bbox labels | PASS | every selected image labeled; normalized and resized-pixel bbox included |
| `detectedAt` remains `T` | PASS | accepted/unavailable/event ID/lastSeenAt checks |
| accept/unavailable emit; reject suppress | PASS | parametrized verdict test |
| One call per region | PASS | simultaneous-region exact boundary test |
| Engine finalize/EOS | PASS | incomplete pending discarded; zero validator calls; frames/state cleared |
| Worker EOS/error finalization | PASS | spy called once on normal EOS and stream exception; source released |
| Demo incomplete post-roll actionable | PASS | compiled path reports count and “provide at least 8 seconds after candidate maturity” |
| Production wiring | PASS | worker receives disabled opt-in, 8/8 seconds, 1 FPS, 17 frames, 480 px, 12 MB |
| Legacy crop path | PASS | temporal-disabled cached single-crop validator regression |
| Demo stationary threshold | PASS | `DEFAULT_CONFIG.stationary_seconds == 6.0` inspection |
| Token not persisted | PASS | scoped credential-pattern scan: zero matches; environment-only lookup retained |

## Compile / Build Status

- `compileall` for changed implementation/demo and all expanded tests: PASS.
- No syntax errors.
- Numeric coverage unavailable: `pytest-cov` absent from vendored environment.

## Full-suite Dependency Failures

- Three `scripts/test_*yolo*.py`: `ModuleNotFoundError: ultralytics`.
- `tests/test_agents/test_graph.py`: `ModuleNotFoundError: langgraph`.
- Same pre-existing collection failures as prior run; not caused by temporal changes.
- Warnings: Starlette/httpx deprecation; unknown asyncio markers because plugin/config unavailable.

## Performance / Determinism

- Payload budget test: 0.28s.
- Oversize rejection: 0.27s.
- 4K buffer test: 0.04s.
- Worker EOS/config tests: <=0.02s each.
- Three repeats stable; no flake observed.

## Critical Issues

- None scoped.

## Recommendations

1. High: install complete requirements; rerun full suite.
2. Medium: add `pytest-cov`; enforce 80% lines/functions and 70% branches.
3. Low: register asyncio plugin/markers; resolve Starlette/httpx warning.

## Exact Commands / Results

```powershell
$env:PYTHONPATH="$PWD;$PWD\.runtime-packages;$PWD\.python-packages"
C:\Users\trand\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m compileall -q app\vlm\region_validator.py app\events\abandoned_object.py app\cv\worker.py scripts\generate_static_abandoned_demo.py tests\unit\test_region_validator.py tests\unit\test_abandoned_object.py tests\unit\test_temporal_full_frame_boundaries.py tests\integration\test_temporal_full_frame_vlm_pipeline.py tests\integration\test_phase4_integration.py
# PASS, no output

.\.runtime-packages\bin\pytest.exe tests/unit/test_region_validator.py tests/unit/test_abandoned_object.py tests/unit/test_temporal_full_frame_boundaries.py tests/integration/test_static_abandoned_pipeline.py tests/integration/test_phase4_integration.py tests/integration/test_temporal_full_frame_vlm_pipeline.py tests/integration/test_temporal_worker_eos.py -q --durations=10
# 32 passed in 1.08s

1..3 | ForEach-Object { .\.runtime-packages\bin\pytest.exe <resource-payload-finalize-selection> -q }
# 4 passed each run; 12 total

.\.runtime-packages\bin\pytest.exe tests/unit/test_region_validator.py tests/unit/test_temporal_full_frame_boundaries.py tests/integration/test_temporal_worker_eos.py -q
# 19 passed in 1.00s

.\.runtime-packages\bin\pytest.exe -q --durations=10
# collection interrupted: 4 missing-dependency errors
```

## Unresolved Questions

- None scoped.
