# Phase 2: Publisher boundary

Status: completed

## Requirements

- Load `EVENT_INGEST_TOKEN`, timeout, retry count, and endpoint from settings.
- Send a bearer credential and stable candidate idempotency key.
- Retry only transient failures with bounded exponential backoff.

## Files

- Modify `app/config.py`, `app/cv/worker.py`, `app/publisher/http_publisher.py`, `.env.example`.
- Update publisher unit tests.

## Success Criteria

- Worker constructs the publisher from settings.
- 401/403/422 do not retry; 408/429/5xx and transport errors do.
- Logs contain request/candidate identifiers but never the token.

## Rollback

- Inject an alternate `EventPublisher`; detector/tracker/rules are unchanged.
