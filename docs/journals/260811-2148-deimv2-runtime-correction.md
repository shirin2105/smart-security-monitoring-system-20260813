# DEIMv2 Runtime Correction After YOLO Survived the Merge

**Date**: 2026-08-11 21:48
**Severity**: High
**Component**: Computer-vision detector and tracker runtime
**Status**: Resolved

## What Happened

The merge accidentally retained the YOLO/Ultralytics production path even though Phase 7A had selected DEIMv2. We corrected the branch by keeping YOLO only on `legacy-yolo`, porting the Phase 7A DEIMv2 runtime, and adopting class-isolated ByteTrack with namespaced IDs. No `back-end/` or `front-end/` files changed.

## The Brutal Truth

We nearly called a model migration complete while the old model still owned production. That is not harmless merge residue; it makes the declared architecture false. The exhausting part was that the first port also looked plausible under narrow tests while carrying startup, import, tracker, and cleanup failures. Review and real execution did the work that optimistic inspection did not.

## Technical Details

Testing exposed `ByteTrackTracker.update(self, detections, frame=None)` being called with the unsupported `timestamp=` argument. Real asset smoke then failed with `ModuleNotFoundError: No module named 'engine'` because the validated DEIM source was not importable in a scoped way. Direct `CVWorker(...)` construction raised `FileNotFoundError` because detector assets were validated eagerly. Review also found permissive/malformed SHA-256 handling and detector construction occurring before the worker cleanup guard.

The fixes added lazy direct-worker initialization, corrected the tracker call, implemented scoped DEIM imports without permanent Docker `PYTHONPATH`, required matching 64-hex checkpoint and backbone hashes before `torch.load(weights_only=False)`, and moved construction inside `try/finally` so source finalization and release still occur on startup failure. External model files remain trusted artifacts only when their pinned hashes match.

## What We Tried

- Initial port plus targeted tests: rejected because it missed real package API and import behavior.
- Global `PYTHONPATH`: rejected because it leaked vendored modules process-wide.
- Optional checksum validation: rejected because absent or malformed digests made artifact identity meaningless.

## Root Cause Analysis

We trusted merge shape and isolated tests instead of verifying the selected runtime end to end. The implementation also encoded guessed dependency contracts and placed fallible initialization outside lifecycle cleanup.

## Lessons Learned

Model-runtime replacement requires a residue scan, dependency-signature test, real artifact smoke, and failure-path cleanup test. A configured path is not proof that imports work; a checksum field is not trust unless validation is mandatory.

## Next Steps

- Main owner: merge the reviewed branch immediately; acceptance is the recorded `MERGE` verdict.
- QA/tooling: add compatible coverage tooling before the next runtime change.
- Runtime maintenance: track upstream deserialization/deprecation warnings during the next dependency update.

Final evidence: full suite `205 passed, 4 skipped`, plus 8 passing subtests; real CPU smoke loaded hash-matched checkpoint/backbone, produced one finite `luggage` detection, and passed scoped import; final review verdict `MERGE`.
