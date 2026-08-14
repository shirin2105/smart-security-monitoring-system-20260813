# Incident LLM Assessment

Status: review blockers fixed; runtime verification blocked by unavailable Python/Docker

## Scope

- Add durable assessment job and immutable versioned assessment records.
- Enqueue exactly once in the same transaction as CV incident persistence.
- Run a backend-local, metadata-only worker with leasing, fencing, retry and fallback.
- Add worker container/env configuration and focused tests.
- Excludes frontend, WebSocket assessment updates, ACK/escalation and mobile.

## Steps

- [x] Add models and backward-compatible schema initialization.
- [x] Add strict metadata snapshot and transactional enqueue.
- [x] Add provider, policy, claim/fencing and worker loop.
- [x] Add Docker/env configuration.
- [x] Add focused ingest, lease/fencing, success, retry and fallback tests.
- [x] Harden durable attempt budget, Postgres claiming, provider I/O and producer schema.
- [x] Add explicit database initialization and fail-closed service ordering.
- [ ] Run compile/tests (no usable Python interpreter in worktree or host launcher).

## Contract note

Jobs become `READY` in the ingest transaction. This is temporary; the realtime branch
will gate readiness until durable provisional publication exists.
