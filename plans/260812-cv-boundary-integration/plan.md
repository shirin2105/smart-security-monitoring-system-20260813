# CV Boundary Integration

Status: completed
Base: `develop@5013006`

## Goal

Deliver the smallest production boundary from the existing DEIMv2 CV pipeline to the existing backend ingest endpoint.

## Scope

- Freeze and validate the canonical `EventCandidate` JSON contract.
- Configure the CV publisher with a producer bearer token, bounded timeout, retry classification, and stable idempotency key.
- Make the existing backend ingest endpoint authenticate producers and deduplicate candidate delivery.
- Add contract and integration tests from publisher payload to persisted incident.

## Excluded

- Backend to LLM orchestration.
- Backend to WebSocket/Web delivery.
- LLM to Web or backend updates.
- Guard ACK/escalation and mobile/push notifications.

## Phases

1. [Contract and fixtures](phase-01-contract-and-fixtures.md) — in progress
2. [Publisher boundary](phase-02-publisher-boundary.md) — pending
3. [Ingest authentication and idempotency](phase-03-ingest-auth-and-idempotency.md) — pending
4. [Verification and handoff](phase-04-verification-and-handoff.md) — pending

## Definition of Done

- A real `EventCandidate` serializes identically at producer and consumer boundaries.
- Publisher sends `Authorization`, `Idempotency-Key`, and `X-Request-ID` without logging secrets.
- Only transport failures, 408, 429, and 5xx retry; other 4xx fail immediately.
- Repeating the same candidate returns a duplicate result without creating another incident.
- CV/runtime and backend boundary tests pass; unrelated component links remain untouched.
