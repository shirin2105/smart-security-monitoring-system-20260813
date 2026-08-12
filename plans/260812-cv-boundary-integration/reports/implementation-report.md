# CV Boundary Implementation Report

Status: implementation complete; runtime verification blocked

- Producer contract frozen; backend consumer accepts the complete candidate shape.
- Publisher sends bearer auth, candidate idempotency key, and request ID.
- Retry is bounded to transport errors, 408, 429, and 5xx.
- Backend authenticates producer, persists candidate identity/hash, suppresses exact duplicates, rejects changed reuse.
- Existing databases receive additive nullable columns and a unique index at startup.
- ORM ingest identity fields are on `Incident`; startup compatibility targets the same table.
- Added boundary coverage for worker config propagation, malformed/empty auth, mismatched keys,
  extra-field rejection, and transport retry.
- Compose injects the required non-empty producer token into the existing backend service; the
  compose file has no CV producer service, so no unavailable service was invented.
- Publisher refuses blank-token delivery before opening a network client.
- `.env.example` intentionally leaves the token empty; README documents generating at least
  32 random bytes and provisioning the same runtime secret to producer and backend.
- Consumer schema now mirrors the canonical producer fields/defaults and rejects non-contract data.
- Incident severity/description derive from canonical event type and observations; unknown cameras,
  unknown event types, and overlong candidate identifiers return explicit 422 responses.
- No backend-to-LLM, WebSocket delivery changes, frontend, mobile, or Guard action work added.
- `git diff --check` passed.
- Tests could not execute: `python` absent, `py` reports no installed Python, direct interpreter execution denied by sandbox.

## Unresolved Questions

- Production token provisioning and rotation remain deployment responsibilities.
- Focused and relevant full Python suites must run once a Python runtime is available.
