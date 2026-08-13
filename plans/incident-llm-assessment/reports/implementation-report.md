# Implementation report

Status: DONE_WITH_CONCERNS

Implemented durable metadata-only assessment in the backend worktree:

- Incident and its single READY assessment job commit atomically.
- Snapshot is explicit allowlist; artifacts, track IDs, imagery, credentials and free text excluded.
- Worker claims READY or expired PROCESSING jobs using token-based fencing.
- Provider runs outside claim transaction; transient calls cap at two attempts.
- Missing credentials, invalid output, timeout and exhausted retries create deterministic fallback.
- Assessment version 1 is unique and does not alter incident severity or status.
- Docker worker reuses backend image and refuses database fallback.

Verification concern: repository `.venv` Python executable is inaccessible and Windows `py`
reports no installed Python. Compile and pytest commands could not execute in this environment.
Docker is also unavailable, so `docker compose config` could not run. `git diff --check` passes.

Accepted review blockers fixed:

- Every provider call consumes a durable fenced attempt before outbound I/O; total cap is two.
- Postgres claims use short `FOR UPDATE SKIP LOCKED` transactions; SQLite retains fencing fallback.
- HTTP 408/429/5xx are transient; other 4xx permanent; response bytes and JSON shape bounded.
- Producer metadata has identifier/string bounds, finite numeric ranges and ordered zoned timestamps.
- Lease configuration covers worst-case two-call timeout budget; worker errors are isolated per job.
- Backend/worker fail closed, credentials/DB URLs are not logged, and both wait for explicit DB init.
- `last_error` contains only bounded fixed categories, never provider exception content.
- Completion atomically requires the same unexpired lease; expiry before reclaim cannot finish.
- SQLite claim uses an eligibility CAS so only one token wins; Postgres retains `SKIP LOCKED`.
- DB/session iteration failures emit a fixed sanitized warning, back off and continue.
- Worker timeout and polling floats reject NaN and infinity during fail-fast startup validation.

Unresolved questions: none.
