# QA Report — Static-region abandoned-object + VLM demo

---
date: 2026-08-01
scope: static-region abandoned-object detector, VLM validation, real-video demo
status: pass-with-concerns
---

## Summary

- Feature-focused compile/tests: PASS.
- Full relevant `tests/unit` + `tests/integration`: 31 passed, 0 failed, 0 skipped in 1.12s.
- Real `aban3.mp4` demo: PASS twice; deterministic event and valid MP4 output.
- Repository-wide starter-template tests: stale/broken independently; excluded from feature gate and reported below.
- Coverage percentages: unavailable; supplied runtime lacks `pytest-cov`.

## Scope and mapping

Git diff unavailable: repository has no `HEAD`; every file is untracked. Focused scope derived from plan-owned code:

- Time/contracts: `app/common/{schemas,time_utils}.py`, `app/sources/mp4_source.py` → timestamp/contract unit tests.
- Static regions: `app/cv/static_region_detector.py` → detector unit tests.
- Event/worker: `app/events/abandoned_object.py`, `app/cv/{detector,worker}.py` → abandoned-object and phase 3 integration tests.
- VLM/demo: `app/vlm/region_validator.py`, `scripts/generate_static_abandoned_demo.py` → validator and phase 4/static-pipeline tests plus manual real-video runs.

## Test results

| Check | Result | Evidence |
|---|---:|---|
| `py_compile` on 18 focused implementation/test files | PASS | exit 0 |
| Focused unit/integration | PASS | 21 passed, 0 failed, 0 skipped; 0.90s |
| All `tests/unit tests/integration` | PASS | 31 passed, 0 failed, 0 skipped; 1.12s |
| Slow tests | PASS | slowest 0.04s; none >5s |
| Coverage | NOT MEASURED | pytest rejects `--cov`; plugin unavailable |

Warnings: Starlette `TestClient`/httpx deprecation; pytest cache cannot write `.pytest_cache` due access denial. Neither failed relevant tests.

## Real-video determinism

Command run twice with distinct outputs: `generate_static_abandoned_demo.py --input tests/clips/aban3.mp4 --vlm local`.

| Property | Run 1 | Run 2 | Status |
|---|---:|---:|---:|
| Source SHA-256 | `866baa28324c9a4d3daf79a788ae261c0792c33e3d19b08bac30b4507e2e93fb` | same | PASS |
| Source before/after hash | same | same | PASS, untouched |
| Alert frame | 450 | 450 | PASS |
| Alert time | 30.0s | 30.0s | PASS |
| Detected at | `2026-08-01T00:00:30.000000Z` | same | PASS |
| Candidate ID | `static-demo-region-48-16-99-74-f450` | same | PASS |
| Events | 1 accepted | identical payload | PASS |
| Output opens | yes | yes | PASS |
| Frames/FPS/dimensions | 2432 / 15.0 / 320×240 | same | PASS |

No synthetic detection feed used: demo imports/updates `StaticRegionDetector` directly from decoded source frames; no detector injection argument or detection payload exists. JSON has no synthetic/injected detection keys. Local VLM verdict was `accepted` based on crop validation; script explicitly notes it does not classify object identity.

## Stale template tests

- `tests/test_agents/test_graph.py`: collection error, missing optional `langgraph` dependency.
- `tests/test_api/test_routes.py`: 3 setup errors, missing `client` fixture; `pytest.mark.asyncio` unregistered because async plugin unavailable in this runtime.
- These tests target starter `src/` agent/API template, not plan-owned `app/` feature. Still prevent a literal repository-wide `pytest` pass.

## Critical issues

None blocking assigned acceptance target.

## Recommendations

1. High: change demo CLI default input from `tests/clips/vtest.avi` to `tests/clips/aban3.mp4`, or align documented selection. Current default contradicts `source_selection` and output filename.
2. Medium: install/configure `pytest-cov`, then set explicit line/branch thresholds. Coverage target cannot be verified.
3. Medium: repair or formally exclude stale `tests/test_api` and `tests/test_agents` in pytest configuration so repository-wide gate has clear meaning.
4. Low: fix `.pytest_cache` permissions and Starlette/httpx deprecation.

## Unresolved questions

- Is `aban3.mp4` now canonical? Assigned acceptance and generated summary say yes; plan and CLI default still say `vtest.avi`.
- What coverage threshold is required? No project threshold/config found; 80% convention not measurable in supplied runtime.
