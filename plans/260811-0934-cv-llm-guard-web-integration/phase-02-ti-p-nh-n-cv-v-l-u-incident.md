---
phase: 2
title: "Tiếp nhận CV và lưu incident"
status: in-progress
priority: P1
effort: 3d
dependencies: [1]
---

# Phase 2: Tiếp nhận CV và lưu incident

## Context Links

- Contract sources: `f04c452:app/cv/contracts/**`, `app/cv/phase8_event_adapter.py`, `app/cv/evidence.py`, `tests/contracts/**`.
- Concept-only backend references: `origin/hiep-01156:back-end/app/api/alerts.py`, `back-end/app/api/auth.py`, `back-end/app/services/websocket.py`.
- Phase 1 ADR/manifest in this plan.

## Overview

Priority P1, in progress, 3d. Authenticated/idempotent ingest, persistence, migrations, adapter, dispatcher and tests implemented. Local suite/review pass; live PostgreSQL verification and ack p95 benchmark remain completion gates.

## Key Insights

- Ack latency must not depend on LLM or WS delivery.
- The database transaction is the consistency boundary; a notification is publishable only after commit.

## Requirements

- Functional: validate three event types; adapt CVEvent v1; upsert candidate lifecycle; create one incident; enqueue provisional alert and enrichment job; expose durable ack.
- Non-functional: p95 ack `<250ms`; replay-safe; restart-safe; transactional; compatible with existing CV producers.

## Architecture / Data Flow

Authenticated CVEvent → schema + camera/zone authorization → adapter → transaction: candidate upsert + conditional incident insert + enrichment job + `INCIDENT_CREATED` outbox → commit → ack. Dispatcher claims rows using `FOR UPDATE SKIP LOCKED`, publishes, and records delivery/retry. CV lifecycle remains candidate metadata.

## Related Code Files

- Modify: `app/api/events.py` or replacement ingest route selected after live architecture trace; `app/cv/contracts/**` only for additive validation.
- Proposed create: backend persistence models/migrations, canonical adapter, ingest service, outbox repository/dispatcher, unit/integration tests. Exact target package is `[UNVERIFIED]` until P1 chooses whether runtime consolidates under `app/` or `src/`.
- Source: paths above; do not port filesystem intake or FastAPI `BackgroundTasks` from `origin/agents:app/services/intake.py`.
- Ownership: migrations/persistence/ingest/adapter/outbox backend files and their tests only.

## Implementation Steps

1. Write failing tests first for mapping, all event types, invalid schema, auth/scope, duplicate/reordered lifecycle, transaction rollback, concurrent duplicates, dispatcher retry/restart.
2. Add forward migration for candidates, incidents, enrichment jobs, outbox and audit-ready version fields; unique constraint on producer/idempotency identity. Provide explicit down migration after compatibility window.
3. Implement one adapter from CVEvent v1 to canonical command; preserve raw factual confidence and string ID; generate numeric incident ID in DB.
4. Implement authenticated ingest with server-side camera/zone scope; reject unsupported event types and unauthorized artifacts.
5. Persist candidate/incident/job/provisional outbox atomically; return ack only from committed state. Abandoned incidents remain `requiresHumanVerification=true`.
6. Implement durable dispatcher with bounded retry, lease/reclaim, poison-row observability and idempotent publish semantics.
7. Benchmark and failure-inject DB rollback, worker crash after publish/before mark, and concurrent replay; document results.

## Todo List

- [ ] Tests-first matrix executed
- [x] Forward/down migrations reviewed
- [x] Adapter is sole CV→backend mapping
- [ ] Atomic ingest/outbox verified
- [ ] Duplicate and crash recovery verified
- [ ] Ack SLO measured

## Expected Outputs

- PostgreSQL schema/migrations, repositories, canonical adapter, secure ingest endpoint, provisional outbox dispatcher.
- Durable ack/error contract and metrics for ingest latency, duplicates, transaction failures, outbox age/retries.
- Unit tests for adapter/state/idempotency; integration tests against real PostgreSQL; controlled publisher fake only for deterministic delivery-failure tests.

## Success Criteria

- `pytest tests/contracts tests/unit tests/integration -q` (target subsets finalized during implementation) passes against PostgreSQL.
- Same event replayed serially/concurrently creates exactly one candidate/incident/job/provisional outbox.
- Forced rollback produces no partial row; restart drains committed pending work.
- Measured ingest ack p95 `<250ms`; provisional publish timestamp enables P5 `<1s` validation.

## Risk Assessment

- High×High duplicate race: DB unique constraint + transactional upsert + concurrency test.
- Medium×High dispatcher double-send: versioned idempotent consumer contract and replay-safe delivery.
- Medium×High migration rollback/data loss: additive schema, dual-read compatibility if needed, backup and delayed destructive cleanup.

## Security Considerations

Service auth with rotation-ready credentials; camera/zone authorization before lookup/mutation; payload limits; parameterized SQL; sanitized logs. Artifact access denied unless redaction COMPLETE and URI authorization succeeds.

## Next Steps / Dependencies

Requires P1. Unblocks P3 enrichment and P4 API/WS/UI. Rollback disables ingest/dispatcher, drains or preserves outbox, then applies down migration only when no dependent deployment reads new tables.

## Progress Evidence (2026-08-11)

- 62+ local tests pass; compile/import checks pass. Seven PostgreSQL integration tests skipped because no `TEST_DATABASE_URL` and Docker unavailable.
- Code-scope review: PASS for Phase 2 implementation.
- Implemented: secure CVEvent endpoint, canonical adapter, PostgreSQL models/migration, transactional ingest, assessment job/outbox, dispatcher, auth/scope handling.
- Completion blocked by: execute 7 tests against live PostgreSQL; measure ingest ack p95 `<250ms`.
- Scope change: none. Phase remains in progress; no completion credit assigned.
