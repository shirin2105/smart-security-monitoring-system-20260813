# Phase 3: Ingest authentication and idempotency

Status: completed

## Requirements

- Authenticate the CV producer at the existing ingest route.
- Persist `candidateId` as a unique incident source identifier.
- Return the original incident for exact duplicate delivery.
- Reject a reused idempotency key carrying a different candidate.

## Files

- Modify backend config, route, service, model/database setup, and tests.

## Success Criteria

- Missing/wrong bearer token is rejected.
- Duplicate delivery creates exactly one incident and broadcasts once.
- Existing alert readers remain compatible.

## Risk

- Existing SQLite databases need an additive column/index migration or startup compatibility path.
