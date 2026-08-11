---
phase: 1
title: "Deterministic video time and contracts"
status: completed
priority: P1
effort: 3h
dependencies: []
---

# Phase 01: Deterministic video time and contracts

## Context Links

- `app/sources/mp4_source.py:31-47` creates frames but stamps wall-clock UTC.
- `app/common/schemas.py:22-29` defines the current frame boundary.
- `app/common/time_utils.py:5-20` provides ISO parsing/duration.
- `app/events/base.py:7-10` fixes the event-engine call contract.

## Overview

Freeze a minimal region/VLM contract and ensure offline video time advances from media position, not processing speed.

## Requirements

- Functional: calculate `captured_at = source_start + frame_index/source_fps`; represent a static region with stable ID, bbox, first/last seen, persistence, and confidence; represent VLM verdict as accepted/rejected/unavailable.
- Non-functional: timezone-aware ISO UTC, deterministic rounding, zero division fallback, no breaking `FrameData` or `EventCandidate` changes.

## Architecture and data flow

`MP4VideoSource(frame_id, FPS, optional start)` -> `video_timestamp_iso()` -> existing `FrameData.captured_at`. Raw detector output becomes immutable `StaticRegionObservation`; optional validator consumes observation + cropped image and returns `VLMValidationResult`. Keep contracts in schemas, not engine state.

## Related Code Files / Ownership

- Modify: `app/common/schemas.py`, `app/common/time_utils.py`, `app/sources/mp4_source.py`
- Create: `tests/unit/test_video_timestamps.py`, `tests/unit/test_static_region_contracts.py`
- Delete: none

## Implementation Steps

1. Add pure timestamp helper taking start ISO, zero-based frame offset, and validated FPS; define invalid-FPS fallback explicitly (25 FPS) and microsecond rounding.
2. Let `MP4VideoSource` capture one start timestamp per source and derive every frame timestamp; synthetic frames use the same path.
3. Add Pydantic contracts for static observations and VLM verdict without adding mutable process-global state.
4. Test first frame, fractional FPS, invalid FPS, repeated runs with fixed start, monotonicity, and serialization.

## Todo List

- [x] Add failing deterministic timestamp tests.
- [x] Add helper and source integration.
- [x] Add static/VLM contracts and serialization tests.
- [x] Run `pytest tests/unit/test_video_timestamps.py tests/unit/test_static_region_contracts.py`.

## Success Criteria

- [x] Fixed start + same frame/FPS yields byte-identical timestamp.
- [x] 300 frames at 25 FPS span exactly 12 seconds by defined indexing.
- [x] Existing `FrameData` callers remain valid.

## Risk Assessment

- High likelihood/high impact: changing time semantics shifts event thresholds. Mitigation: explicit tests, fixed indexing convention, integration baseline before cutover.
- Medium likelihood/medium impact: variable/invalid FPS metadata. Mitigation: one documented fallback and warning; never wall-clock fallback for files.

## Security Considerations

No external data transfer. Validate timestamp/FPS inputs; do not log source credentials embedded in URIs.

## Rollback

Revert source/helper changes; schema additions are additive and may remain safely.

## Next Steps

Phase 02 consumes the frozen observation contract and deterministic frame clock.
