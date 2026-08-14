# Test Report — 2026-08-12 — CV to Web demo

## Diff-aware scope
- Changed/new implementation: `app/cv/demo_flow.py`, `app/cv/demo_cli.py`, `app/publisher/http_publisher.py`, `configs/cv-web-demo.yaml`.
- Mapped tests: `tests/unit/test_cv_web_demo.py`, `tests/unit/test_http_publisher.py`, `back-end/tests/test_api.py`, `front-end/src/api/adapters.test.ts` (co-located/import/contract mapping).
- Unmapped critical path: `run_demo()` has no direct unit/integration test.

## Test Results Overview
- Python: 0 run. Blocked: `python` absent; `py -3.11` reports `No installed Python found!`.
- Frontend: 0 run. `npm test` blocked: `vitest` absent. Build blocked: `tsc` absent.
- Static diff check: pass; only Git LF→CRLF warnings.
- E2E real DEIMv2: 0 run. Source, checkpoint, backbone absent.

## Coverage Metrics
- Lines/branches/functions: unavailable; no runnable Python or frontend dependencies.
- Requirement coverage: receipt unit test exists; frontend envelope assertion exists. WS-before-CV, matching WS/REST, baseline exclusion, duplicate no-rebroadcast, real-DEIM checks not dynamically tested.

## Build Status
- Python compile: blocked by missing runtime.
- Frontend production build: blocked by missing dependencies.

## Critical Issues
1. `run_demo()` critical orchestration has no test. Current tests only check stable config and blank-token error. Regressions in socket ordering, matching IDs, REST persistence, duplicate receipt, and no-rebroadcast pass unnoticed.
2. No-LLM dependency not guaranteed. `CVWorker` uses `configs/event_rules.yaml` with abandoned-object VLM mode `huggingface`; demo config does not override/disable it. A static abandoned candidate can attempt external Hugging Face validation and alter/timing-block demo behavior.
3. Real demo unverifiable in current checkout: `third_party/deimv2`, checkpoint, and backbone missing. Preflight should fail as documented; successful MP4→alert not demonstrated.
4. Duplicate no-rebroadcast check watches only 0.5 s. A delayed duplicate broadcast after 0.5 s yields false pass; no deterministic backend integration assertion covers this orchestration.

## Verified static behavior
- WebSocket context opens before worker construction/run: `app/cv/demo_flow.py:72-75`.
- Baseline collected before WebSocket/CV and incident matched by receipt ID over WS and REST: lines 71, 77-92.
- Duplicate receipt requires `DUPLICATE_IGNORED`; same incident rebroadcast within window fails: lines 93-103.
- Real-mode preflight checks sample readability, services, source dir, checkpoint/backbone presence and SHA-256: lines 41-65.
- Token blank error does not include token; publisher logs candidate/request/status only.
- Stable sample tracked in Git: `examples/intrusion_positive_demo.mp4`, 1,206,222 bytes.

## Recommendations
1. Block merge until test/build run in installed environments and pass.
2. Add async `run_demo()` tests with fake HTTP/WS/worker boundaries for ordering, receipt match, REST baseline, unrelated WS messages, duplicate no-broadcast, malformed/non-2xx REST.
3. Make demo explicitly CV-only by disabling VLM for this run or injecting a demo-specific worker configuration.
4. Test all preflight failures: unreadable video, service failure, missing source/model keys/files, checksum mismatch; assert secrets absent from exception/log output.
5. Use a deterministic server-side assertion or configurable grace interval for duplicate no-rebroadcast.

## Unresolved Questions
- Is Hugging Face VLM intentionally allowed during this CV-only demo? Plan says LLM out of scope.
- What environment supplies the pinned DEIMv2 source/checkpoint/backbone for the acceptance run?
