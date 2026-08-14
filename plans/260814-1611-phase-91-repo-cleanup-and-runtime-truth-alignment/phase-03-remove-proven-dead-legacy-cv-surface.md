---
phase: 3
title: "Remove proven-dead legacy CV surface"
status: pending
priority: P1
effort: "4h"
dependencies: [1, 2]
---

# Phase 3: Remove proven-dead legacy CV surface

## Overview

Delete only legacy static-region/VLM abandoned-object code, its standalone demo, and tests once Phase 1 proves they are disconnected from active Phase 9 execution. Do not touch backend/agent `EventCandidate` compatibility paths.

## Data flow and lifetime checks

Current worker state is per `CVWorker` instance: tracker/store/adapters/manager/publisher are created at `app/cv/worker.py:65-84`, then frame data flows through detector, tracker, one immutable store snapshot, adapters, manager, validation, publisher (`:88-168`). Candidate legacy state instead lives behind `app/events/abandoned_object.py:182`, `app/cv/static_region_detector.py:26`, and `app/vlm/region_validator.py:49-254`. Removal is allowed only if no production entry point reaches this latter graph; do not add a shared replacement state or modify current lifetimes.

## Related files and ownership

- Conditional delete (exclusive; only if Phase 1 audit permits): `app/vlm/__init__.py`, `app/vlm/region_validator.py`, `app/cv/static_region_detector.py`, `app/events/abandoned_object.py`, `scripts/generate_static_abandoned_demo.py`.
- Conditional delete (exclusive, matched to removed code): `tests/unit/test_region_validator.py`, `tests/unit/test_static_region_detector.py`, `tests/unit/test_abandoned_object.py`, `tests/unit/test_temporal_full_frame_boundaries.py`, `tests/integration/test_production_vlm_configuration.py`, `tests/integration/test_temporal_full_frame_vlm_pipeline.py`, `tests/integration/test_static_abandoned_pipeline.py`, `tests/integration/test_static_abandoned_demo_decisions.py`.
- Conditional update (exclusive): `configs/cv-web-demo.yaml`, `app/cv/demo_flow.py`, and their tests only if Phase 1 traces a real dependency. Do not change them merely because a VLM-disabled preflight string exists.
- Explicitly retain: `app/common/schemas.py:66`, `app/publisher/http_publisher.py:5-30`, `app/api/events.py:6-28`, `app/services/intake.py:18-81`, agent modules, and their tests: they are out-of-scope backend/LLM compatibility, not CV runtime cleanup.

## Implementation steps

1. Convert every Phase 1 `delete` candidate into a direct-import and entry-point proof. The known legacy demo imports all three legacy components (`scripts/generate_static_abandoned_demo.py:19-21,70-76`); delete its matched tests in the same atomic change.
2. Before deletion, grep the full repository for direct imports and dynamic strings. If any active caller remains, retain the component and annotate it as legacy; do not introduce shims, aliases, deprecation wrappers, or new classes.
3. Delete matched code/tests in one focused commit. Do not delete generic schemas, old reports, datasets, artifacts, or Phase7C core/adapters.
4. Re-grep `app.vlm`, `StaticRegionDetector`, `AbandonedObjectEngine`, `candidate_source: static_regions`, VLM models, YOLO/Ultralytics/StrongSORT. Classify all residual hits; a residual is acceptable only in a clearly labelled historical report/doc, protected backend compatibility, or external ignored artifact.
5. Inspect `git diff --name-status` against Phase 1 inventory. Any path outside exclusive ownership stops the phase for review.

## Test matrix

| Level | Check | Protects |
|---|---|---|
| Unit | `test_cv_event_manager.py`, `test_jsonl_publisher.py`, `test_cv_worker_publisher_config.py`, Phase7C adapter/unit suite | lifecycle identity, JSONL schema, config validation, abandoned temporal facts. |
| Integration | `test_unified_cv_worker.py`, `test_temporal_worker_eos.py`, `test_deimv2_worker_runtime.py`, Phase7C production integration | one flow, cleanup/release, detector-start behavior. |
| Negative static | `python -c` imports of the active worker/Phase7C adapter plus grep | no removed module import is hidden behind active runtime. |

## Risks and mitigation

| Risk | Likelihood × impact | Mitigation / rollback |
|---|---|---|
| Deleting a test hides an active regression | Medium × High | Delete tests only with their dead subject; retain/replace protections for the live Phase7C flow. |
| `cv-web-demo` crosses backend scope | Medium × High | Audit its call graph first; exclude it if it depends on the legacy compatibility demo. |
| Removal breaks an undocumented consumer | Medium × Medium | Keep changes in one revertible commit; final focused import/test gate is required before merge. |

## Success criteria

- [ ] Every deleted path is documented in the audit with zero active dependency proof.
- [ ] Current production imports of `app.vlm` and `StaticRegionDetector` equal zero.
- [ ] Current Phase 9 worker, contract, lifecycle, and publisher tests still exist and pass.

## Rollback

Revert the single legacy-surface deletion commit; then re-run the Phase 4 focused suite. No data migration, config migration, or event-schema migration is required.

## Next steps

Phase 4 validates the retained runtime and records final residual grep classifications.

