# Phase 1: Contract and fixtures

Status: completed

## Requirements

- Make `EventCandidate` immutable after validation.
- Provide representative contract payloads for intrusion, crowd, and abandoned-object events.
- Validate complete producer payloads at the backend boundary.

## Files

- Modify `app/common/schemas.py` and backend ingest schema.
- Add focused contract fixtures/tests under `tests/` and `back-end/tests/`.

## Success Criteria

- Mutation fails validation.
- Producer JSON is accepted without field loss or incompatible defaults.
- No CV image matrix crosses the boundary.

## Security

- Metadata only; artifact remains a URI and redaction state.
