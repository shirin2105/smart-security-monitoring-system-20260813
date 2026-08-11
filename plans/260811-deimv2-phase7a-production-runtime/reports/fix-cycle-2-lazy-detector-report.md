# Fix cycle 2: lazy direct-worker detector

## Diagnosis

- Symptom: six existing worker tests raise `FileNotFoundError` during `CVWorker(...)` construction.
- Root cause: `CVWorker.__init__` eagerly instantiated `DEIMv2Detector`, whose strict asset validation ran before tests or callers could finish configuring the worker.
- Expected: direct workers validate at `run()` entry, before source reads; injected detectors remain accepted. `MultiCameraRunner` stays eager because it owns the shared model.
- Blast radius: direct `CVWorker` callers and worker integration tests. Shared multi-camera construction and locking remain unchanged.

## Changes

- Added optional detector factory seam; resolve once at start of `CVWorker.run`, before `read_frames`.
- Kept injected detector behavior and eager `MultiCameraRunner` shared detector validation.
- Added timing/failure regression tests plus detector asset, threshold, empty-frame, and image-shape coverage.
- Added `CONFIG_DIR` and `DEIMV2_{SOURCE,CONFIG,CHECKPOINT,BACKBONE}_PATH` overrides.
- Pinned verified environment: torch 2.5.1, torchvision 0.20.1, Pillow 12.2.0, supervision 0.30.0, trackers 2.5.0.post0.

## Verification

- `python -m compileall -q app tests`: pass with configured Python 3.11 interpreter.
- Constructor/lazy ordering smoke: pass; observed `factory -> read -> finalize -> release`.
- Detector guard smoke: pass for empty image and invalid image shape.
- Runtime import versions: `2.5.1+cu124`, `0.20.1+cu124`, `12.2.0`, `0.30.0`, `2.5.0.post0`.
- Full pytest unavailable: embedded interpreter lacks pytest; installation failed because network access is blocked.

## Unresolved Questions

- Coverage percentage cannot be measured until pytest/coverage is installed in the verified interpreter.
- Real checkpoint inference requires provisioning the configured checkpoint in this worktree.
