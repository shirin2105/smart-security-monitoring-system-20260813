---
phase: 5
title: "Remove legacy runtime and update docs"
status: completed
priority: P2
effort: 1d
dependencies: [4]
---

# Phase 5: Remove legacy runtime and update docs

## Overview

After recorded regression PASS only, remove active VLM/static-region abandoned code/config and stale YOLO/Ultralytics claims. Preserve clearly labeled historical records.

Progress: complete. Active production VLM/static-region and stale YOLO/Ultralytics/StrongSORT routes removed; retained material legacy-classified. Backend, LLM, and Phase 10 unchanged.

## Gate Tracking

- [x] Phase 4 required automated + video regression PASS recorded.
- [x] Explicit cleanup authorization recorded.
- [x] Active legacy runtime cleanup and classification completed.

## Related Code Files / Exclusive Ownership

- Delete after zero callers: `app/cv/static_region_detector.py`, `app/vlm/__init__.py`, `app/vlm/region_validator.py`; obsolete unit/integration tests dedicated to those paths.
- Modify dependencies only if unused elsewhere: `requirements.txt`, Docker/config manifests.
- Modify current docs: `docs/system-architecture.md`, `docs/development-roadmap.md`, `docs/project-changelog.md`, `docs/architecture_diagram.md`, root `README.md`, `docs/README.md`.
- Historical journals remain; add legacy marker only if search context is misleading.

## Implementation Steps

1. Verify Phase 4 evidence and tag cleanup commit boundary.
2. Re-grep exact terms: `app.vlm`, `region_validator`, `HuggingFaceRegionValidator`, `StaticRegionDetector`, `candidate_source: static_regions`, `gemma`, `VLM`, `YOLO`, `yolo26m`, `ultralytics`, `StrongSORT`.
3. Classify every hit: active runtime remove; current docs update; historical docs retain/label; dead scripts delete/archive.
4. Remove old config only now. Remove dependency only if full repository caller/dependency grep proves unused (for example `httpx` remains needed by publisher/demo, so do not remove it solely with VLM).
5. Run compile, focused/full tests, video smoke. Re-run grep and attach results.
6. Update architecture flow, migration map, rollback instructions, known limitations.

## Success Criteria

- [x] Production CV has zero active import/config/runtime path to VLM/static regions.
- [x] Production detector/tracker claims are DEIMv2/ByteTrack; zero active YOLO/Ultralytics/StrongSORT route.
- [x] Historical evidence preserved and clearly non-current.
- [x] Required CV tests and post-cleanup 4/4 video regression pass; current architecture matches live CV code.

## Risks / Rollback / Security

- High × High: premature deletion destroys fallback. Mitigation: hard dependency on Phase 4 PASS; separate cleanup commit; pre-delete caller enumeration.
- Medium × High: remove shared dependency used outside VLM. Mitigation: dependency-level usage grep; `httpx` known shared at `app/publisher/http_publisher.py:3` and CV demo.
- Rollback: revert cleanup commit only; Phase 3 unified path remains unchanged. If post-cleanup regression fails, restore deleted modules/config while diagnosing.

## Final Report

List created/modified/deleted files; final flow; old→new abandoned mapping; three sample events; commands/results; Phase7C/video/webcam evidence; remaining grep hits with classification; dependency changes; known issues; merge readiness. Explicitly state no Phase10/backend/frontend/LLM work.

## Unresolved Questions

None for CV merge readiness. Webcam hardware verification remains user manual.
