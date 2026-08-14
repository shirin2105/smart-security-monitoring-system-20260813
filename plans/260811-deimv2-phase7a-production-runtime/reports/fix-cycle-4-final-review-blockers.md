# Fix cycle 4 — final review blockers

## Root causes and fixes

- Artifact checks accepted absent/malformed digests, so `torch.load(weights_only=False)` could run without identity proof. Production detector now requires matching 64-hex checkpoint/backbone SHA-256 values; shipped hashes pinned.
- Detector construction preceded `CVWorker.run()` cleanup guard. Construction moved inside `try/finally`; representative constructor-path test proves finalize/release on startup failure.
- Docker permanently exposed vendored DEIMv2 through `PYTHONPATH`. Removed; scoped importer remains authoritative.
- `LockedDetector` serialization lacked concurrent evidence. Five simultaneous callers now assert maximum in-flight detector calls equals one.
- `_first_seen` grew forever. Installed tracker package unavailable to inspect in current shell; bounded pruning uses configured `lost_track_buffer`, preserving missed-frame revival then resetting first-seen on post-expiry ID reuse.
- `.qa-tmp/` cleanup prohibited by policy. Exact directory added to `.gitignore`; no files deleted.

## Verification

- `compileall app tests`: PASS.
- `configs/models.yaml` parse plus both 64-character hashes: PASS.
- `git diff --check`: PASS; existing line-ending warnings only.
- Focused pytest: environment blocked before collection. Available Python is CPython 3.12; cached project native packages are CPython 3.11 (`numpy`/`pydantic_core` ABI mismatch). Previous compatible-environment baseline was 196 passed, 4 skipped, 8 subtests.

## Unresolved questions

- Rerun focused and full pytest under the project's dependency-complete CPython 3.11 environment before merge.

**Status:** DONE_WITH_CONCERNS
**Summary:** All requested production blockers and high-value gaps fixed; static/config gates pass.
**Concerns/Blockers:** Fresh pytest execution blocked only by local Python ABI mismatch; compatible CPython 3.11 rerun remains.
