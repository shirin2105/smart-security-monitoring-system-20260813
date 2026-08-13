---
role: tester
date: 2026-08-01
scope: temporal-vlm-final-regression
status: passed
---

# Test Report — Temporal VLM final regression

## Test Results Overview

- Relevant unit/integration/demo tests: 34 passed, 0 failed, 0 skipped.
- Duration: 1.29s.
- Compile: PASS; no output/errors.
- Implementation edits: none.

## Verified

- Original temporal timing/window/verdict/timestamp/call-count/cleanup/legacy matrix.
- Full-scene proportional resizing, memory ceiling, serialized request ceiling, oversize no-network.
- Offset/bbox labels, endpoints, event-nearest compatibility selection.
- Engine and worker EOS finalization; production temporal configuration.
- Demo records rejected semantic decisions independently of emitted alerts.
- Unavailable demo outcome writes sanitized, auditable diagnostics and raises actionable failure.
- Updated `AppConfig` loads production YAML values: PASS.

## Artifact Validation

- JSON artifacts discovered: 6.
- JSON parsed: 6/6; invalid: 0.
- Token/bearer/key-field pattern hits: 0.
- MP4 artifacts opened: 2/2.
- JPEG diagnostics decoded: 11/11.
- Both current PETS summaries parse and include source hash, source-integrity field, and validation-decision count.

## Performance

- Slowest: aggregate payload test 0.29s; oversize no-network 0.28s.
- Demo rejection decision test 0.08s; sanitized unavailable diagnostics test 0.03s.

## Exact Commands / Results

```powershell
$env:PYTHONPATH="$PWD;$PWD\.runtime-packages;$PWD\.python-packages"
C:\Users\trand\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m compileall -q app\config.py app\vlm\region_validator.py app\events\abandoned_object.py app\cv\worker.py scripts\generate_static_abandoned_demo.py tests\unit\test_region_validator.py tests\unit\test_abandoned_object.py tests\unit\test_temporal_full_frame_boundaries.py tests\integration\test_temporal_full_frame_vlm_pipeline.py tests\integration\test_phase4_integration.py tests\integration\test_temporal_worker_eos.py tests\integration\test_static_abandoned_demo_decisions.py
# PASS; no output

.\.runtime-packages\bin\pytest.exe tests/unit/test_region_validator.py tests/unit/test_abandoned_object.py tests/unit/test_temporal_full_frame_boundaries.py tests/integration/test_static_abandoned_pipeline.py tests/integration/test_phase4_integration.py tests/integration/test_temporal_full_frame_vlm_pipeline.py tests/integration/test_temporal_worker_eos.py tests/integration/test_static_abandoned_demo_decisions.py -q --durations=15
# 34 passed in 1.29s
```

## Coverage Metrics

- Numeric coverage not collected; `pytest-cov` unavailable in provided runtime.

## Critical Issues

- None scoped.

## Recommendations

1. Install `pytest-cov` in canonical dev environment; record line/branch/function metrics.

## Unresolved Questions

- None.
