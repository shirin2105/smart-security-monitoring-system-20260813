# Project Changelog

## 2026-08-11

### Changed

- Replaced the active YOLO/Ultralytics detector and greedy tracker with the frozen DEIMv2 Phase 7A runtime and two class-isolated ByteTrack instances. Production code, configuration, dependencies, and Docker contain no YOLO/Ultralytics runtime reference; the prior implementation remains available only on the `legacy-yolo` branch.
- Made DEIMv2 source, checkpoint, and DINOv3 backbone externally provisioned, read-only deployment inputs. Startup requires pinned SHA-256 values before checkpoint deserialization and fails fast for missing or mismatched assets, incompatible weights, or unavailable explicit CUDA. There is no detector fallback.
- Added `CONFIG_DIR` and `DEIMV2_SOURCE_PATH`, `DEIMV2_CONFIG_PATH`, `DEIMV2_CHECKPOINT_PATH`, and `DEIMV2_BACKBONE_PATH` overrides. A backbone override must remain paired with the selected runtime YAML.

### Verification notes

- Final gate: compile passed; targeted runtime tests passed 25/25; modified legacy integrations passed 6/6; full suite passed 205 tests with 4 skips and 8 passing subtests.
- A real-asset CPU smoke loaded the pinned Phase 7A checkpoint and DINOv3 backbone without global `PYTHONPATH`, then returned one finite `luggage` detection from a 320x512 zero frame.
- Coverage tooling was unavailable, so no coverage result is claimed. See [`system-architecture.md`](./system-architecture.md) for runtime ownership and deployment constraints.

## 2026-08-10

### Added

- **2026-08-10 — Agent architecture deepening:** delivered the private LangGraph assessment runner, authoritative advisory policy, typed legacy-compatible assessment records, and observable best-effort handoff in four vertical TDD slices. `EventCandidate`, ingest behavior, and persisted record shape remain compatible; crash recovery is not claimed.
- Completed the Phase 7B.1 Kaggle generic-luggage tracking runtime. The 2,189-frame run produced 17 tracks and 5,019 valid JSONL observations at 20.10 FPS; cross-class luggage merge/NMS removed 21,630 of 35,762 raw luggage boxes. The result report explicitly records that zero background anchors were learned and no abandoned-object alarm or MOT-quality claim is made.

## 2026-08-01

### Added

- Class-independent static-region detection with baseline warm-up, persistence, clearing, and re-arming identities.
- `static_regions` candidate routing through the abandoned-object engine, including owner-absence timing, cached validation, evidence capture, and deduplication.
- Deterministic UTC video timestamps derived from source epoch, zero-based frame offset, and source FPS.
- Hugging Face multimodal validator using environment-only `HF_TOKEN`, strict JSON parsing, bounded image/request settings, and explicit unavailable results.
- Bounded `MultiCameraRunner` supervision for up to six enabled cameras with a shared lock-protected detector and per-camera failure isolation.
- Canonical PETS real-data generator, annotated video, and JSON summary with source integrity and semantic-validation disclosure.
- Temporal full-scene validation: proportional 480-pixel sampling at 1 FPS over `T-8s..T+8s`, an 8-second post-roll wait, maximum 17 frames, 12 MB per-camera memory ceiling, and 12 MB aggregate Hugging Face request budget.
- End-of-stream cleanup that drops incomplete temporal windows without validation or event emission and reports incomplete region IDs.

### Changed

- Default abandoned-object configuration now selects `candidate_source: static_regions`.
- Heuristic validation is named and disclosed as non-semantic; compatibility alias `local` remains accepted internally, but the demo CLI exposes `disabled`, `heuristic`, and `huggingface`.
- Validator unavailability fails open at the event engine; explicit rejection suppresses the candidate.
- Deferred temporal decisions preserve the original candidate timestamp `T` in emitted events rather than using the later decision time.
- Production abandoned-object configuration now enables temporal Hugging Face validation by default with `google/gemma-3-4b-it`.
- Worker construction performs no provider request. With no `HF_TOKEN`, validation returns `unavailable` without network access after the 8-second post-roll wait, and the event engine fails open.
- The canonical demo static-region threshold is now 6 seconds.

### Verification notes

- The committed authenticated PETS summary records one real Hugging Face decision over 16 ordered full-scene frames. The model identified the region as a person and rejected it at `0.99` confidence, so no alert was emitted.
- The detector/heuristic PETS comparison processed all 1,510 frames and emitted three alerts; the first occurred at 45.5 seconds and `semantic_vlm_executed` is `false`.
- The six-camera behavior is contract-tested only. No real six-camera performance benchmark has been completed.
- The PETS artifact demonstrates execution on real footage; it is not a labeled accuracy benchmark.

See [`system-architecture.md`](./system-architecture.md) for the verified command, artifacts, behavior, and limitations.
