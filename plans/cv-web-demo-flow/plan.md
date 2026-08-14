# CV to Web demo flow

Status: implemented; runtime verification blocked by missing local dependencies

## Scope

- Add an isolated `cam_01` MP4 demo configuration and one PowerShell command.
- Validate services, media, token, and real DEIMv2 assets before processing.
- Subscribe to WebSocket first, run CV, then verify the same accepted incident over WebSocket and REST.
- Preserve `CVWorker.run()` and production camera defaults; provide injection seams for tests.

## Acceptance

- Real DEIMv2 is the default; test callers may inject a worker.
- Success means an accepted publish receipt, matching `NEW_ALERT`, and persisted CV incident for camera 1.
- Re-publishing the same candidate is reported as duplicate and emits no second alert.
- Every wait is bounded and failures identify their stage without exposing the token.
- Frontend tests lock the production `NEW_ALERT` envelope and the frontend build passes.

## Out of scope

WebSocket authentication, service hardening, LLM, ACK/escalation, and mobile.

## Steps

- [x] Add publish receipt seam without changing the worker return type.
- [x] Add demo config, preflight, orchestration, and CLI.
- [x] Add backend/frontend/CLI tests and operator documentation.
- [x] Add per-run candidate correlation, cooperative timeout, and full duplicate observation.
- [x] Isolate production CV execution in a Windows-safe spawned process with definitive timeout cleanup.
- [ ] Run Python tests and frontend test/build gates (Python absent; npm install blocked by cache permissions).
