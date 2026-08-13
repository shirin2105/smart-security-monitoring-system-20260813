# Test Report — 2026-08-12 — CV Boundary Verification

---
role: tester
scope: CV producer to authenticated backend ingest boundary
status: blocked
---

## Summary

- Diff-aware mode: 12 changed tracked files.
- Scope contained to producer + backend ingest. No frontend, mobile, LLM adapter, or WebSocket implementation file changed.
- Dynamic execution blocked: every discovered Python launcher returns `Access is denied`; Docker unavailable.
- Static review found blocking ORM/schema mismatch.

## Diff Mapping

- Changed producer: `.env.example`, `app/common/schemas.py`, `app/config.py`, `app/cv/worker.py`, `app/publisher/http_publisher.py`.
- Mapped tests: `tests/unit/test_event_candidate_schema.py`, `tests/unit/test_http_publisher.py` (co-located/import mapping).
- Changed backend: `back-end/app/api/events_ingest.py`, `back-end/app/db/database.py`, `back-end/app/db/models.py`, `back-end/app/services/ingest.py`.
- Mapped test: `back-end/tests/test_api.py` (backend integration/API mapping).
- Unmapped direct worker wiring: `app/cv/worker.py` has no new assertion verifying token/timeout/max-attempt propagation.

## Test Results Overview

- Tests executed: 0
- Passed: 0 | Failed: 0 | Skipped: 0
- Collection never started; environment failure exit code 101.
- Requested commands attempted: `compileall`, focused producer tests, focused backend API tests.
- Error: `Unable to create process ... python.exe ... Access is denied.`
- Discovered repo `.venv` points to `C:\Users\trand\AppData\Local\Python\pythoncore-3.14-64\python.exe`; direct execution also denied.
- Bundled skill `.venv` launcher also denied. `docker` command not installed.

## Coverage Metrics

| Metric | Value | Threshold | Status |
|---|---:|---:|---|
| Lines | unavailable | 80% | BLOCKED |
| Branches | unavailable | 70% | BLOCKED |
| Functions | unavailable | 80% | BLOCKED |

## Critical Issues

1. **BLOCKING — idempotency columns declared on wrong ORM model.**
   - `back-end/app/db/models.py` adds `candidate_id` and `payload_hash` to `Camera`.
   - `back-end/app/db/database.py` migrates these columns on `incidents`.
   - `back-end/app/services/ingest.py` queries/sets `Incident.candidate_id` and `Incident.payload_hash`.
   - Result: `Incident` lacks referenced mapped attributes; ingest initialization/query fails before idempotency behavior can work.

2. **Coverage gap — worker configuration wiring.**
   - No focused test verifies `CVWorker` constructs publisher with `event_ingest_token`, timeout, and max attempts.

3. **Coverage gap — boundary validation/error branches.**
   - No explicit tests for mismatched `Idempotency-Key`, forbidden extra payload fields, empty server token, malformed authorization scheme, or transport exceptions.

## Performance Metrics

- Unavailable; tests could not start.
- Retry tests mock sleep, so no expected intentional delay in focused suite.

## Build Status

- Python compile: BLOCKED by interpreter execution policy.
- Dependency resolution: not validated.
- Dynamic backend compatibility: not validated.

## Scope Verification

- `git diff --name-status HEAD`: no `front-end/`, mobile, LLM adapter, or WebSocket source changes.
- Backend ingest continues broadcasting through existing WebSocket manager, but no backend↔Web implementation file changed.

## Recommendations

1. Critical: move `candidate_id` and `payload_hash` ORM columns from `Camera` to `Incident`; rerun focused backend tests.
2. High: run compileall and mapped tests in an environment allowed to execute repo Python.
3. High: add worker wiring test and explicit boundary negative cases.
4. Medium: run relevant full Python suites and coverage after focused tests pass.

## Unresolved Questions

- Which CI/local runtime should be authoritative for Python 3.11+ verification? Current repo `.venv` uses Python 3.14.4 and is not executable in this sandbox.

## Retest — Final Static Verification

- Previous ORM blocker resolved: both fields now declared on `Incident`; migration, queries, inserts, and duplicate comparison consistently target incidents.
- Negative boundary tests now structurally cover empty configured token, malformed bearer scheme, mismatched idempotency key, top-level/nested extra fields, duplicate conflict, and publisher transport retry.
- Worker wiring test added at `tests/unit/test_cv_worker_publisher_config.py`; verifies URL, bearer token, timeout, and attempts propagation.
- Scope remains contained: no frontend, mobile, LLM adapter, or WebSocket implementation changes.
- Runtime attempted once; pytest still failed before collection with exit 101 / `Access is denied`.
- Remaining correctness blockers from static inspection: none.
- Final QA status: **BLOCKED** only because compile/tests/coverage cannot execute in current sandbox.
