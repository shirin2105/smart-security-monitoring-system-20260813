# Test Report — 2026-08-12 — Incident LLM assessment

## Diff-aware scope

- Changed: `.env.example`, backend database/models/ingest, 3 assessment services, `docker-compose.yml`, new assessment tests.
- Mapped: `back-end/tests/test_assessment.py`, `back-end/tests/test_api.py` via co-location/import graph and backend config impact.
- Scope guard: no changed files in `front-end/`, `mobile/`, root `app/`, backend WebSocket/API/main.
- `git diff --check`: PASS; LF-to-CRLF warnings only.

## Test Results Overview

- Focused backend: 0/18 executed; BLOCKED by missing executable Python runtime.
- Full backend: 0/18 executed; same blocker.
- Relevant root/full suite: 0/136 discovered test functions executed; same blocker.
- Compileall: BLOCKED.
- Passed/failed/skipped: 0/0/0; results unavailable, not a pass.
- Flake/performance: not measurable.

## Exact environment failures

- `python --version`: command unavailable.
- `python3 --version`: command unavailable.
- `py --version`: `No installed Python found!`
- root `.venv\Scripts\python.exe --version`: `Unable to create process ... Access is denied.`
- venv base runtime points to `C:\Users\trand\AppData\Local\Python\pythoncore-3.14-64\python.exe`, unavailable to this session.
- `docker --version`: command not found.
- `wsl --status`: WSL not installed.
- Compose parse fallback unavailable: PowerShell `ConvertFrom-Yaml` not installed.

## Coverage Metrics

| Metric | Value | Threshold | Status |
|---|---:|---:|---|
| Lines | unavailable | 80% | BLOCKED |
| Branches | unavailable | 70% | BLOCKED |
| Functions | unavailable | 80% | BLOCKED |

## Static test-gap review

- No direct boundary tests for `validate_assessment`: invalid type, blank values, 500/1000 limits, whitespace trimming.
- No provider transport tests: timeout/URL failure, malformed JSON/schema, HTTP 4xx vs 5xx classification.
- No worker-loop resilience test when unexpected provider/database exceptions escape `process_claim`/`main`.
- Success test checks row count but not persisted outcome/summary/rationale/provider/fallback values.
- Fallback tests do not assert deterministic fallback content/provider for permanent error.
- No lease-expiry-during-provider-call test.
- No restart recovery test against PostgreSQL; SQLite tests cannot validate PostgreSQL concurrency/locking semantics.

## Build Status

- Python syntax/build: BLOCKED; no runnable interpreter.
- Docker Compose config/build: BLOCKED; Docker unavailable.
- Config source inspection: worker service present, PostgreSQL health dependency present, fail-closed DB enabled.

## Critical Issues

1. Quality gate cannot be signed off: zero tests and zero compile checks executed.
2. PostgreSQL behavior unverified; job claiming and lease fencing are concurrency-sensitive.

## Recommendations

1. P0: run with accessible Python 3.10+ and dependencies, then `python -m compileall back-end/app back-end/tests`.
2. P0: from `back-end`, run `python -m pytest tests/test_assessment.py -q`, then `python -m pytest tests -q`.
3. P0: from repo root, run `python -m pytest tests back-end/tests -q`; repeat focused suite 3x for flake check.
4. P0: run `docker compose config`, build/start PostgreSQL + worker, verify restart/reclaim behavior.
5. P1: add tests for static gaps above; generate `pytest --cov` metrics and enforce thresholds.

## Unresolved Questions

- Can CI or another approved shell provide Python/Docker execution for final verification?
- Are PostgreSQL migrations intentionally replaced by `create_all`, or is a migration artifact pending?
