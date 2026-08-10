# Project Changelog

## 2026-08-10

### Changed

- Split the previous YOLO and multimodal-validation implementation into the `legacy-yolo` branch.
- Removed the legacy detector, worker, static-region detector, semantic validator, abandoned-object engine, configs, tests, plans, demo videos, and bundled test clips from the active branch.
- Removed the `ultralytics` runtime dependency and updated the remaining intrusion/crowd event metadata to identify the Phase 7A DEIMv2 checkpoint.
- Simplified the FastAPI entrypoint to health, debug, and event-ingestion routes; it no longer exposes the legacy detector demo.
- Reframed architecture and roadmap documentation around the active DEIMv2, ByteTrack, Phase 7C, Phase 8, and `cv-event-v1` flow.

### Added

- Added the Phase 8.9 `cv-event-v1` handoff contract for intrusion, crowd, and candidate-only abandoned events, including lifecycle validation and JSONL IO.
- Added Phase 8 CV-only validation tooling and the CAVIAR validation-set workflow.
- Added the Phase 8.5 local DEIMv2/ByteTrack webcam test and start/stop launchers.

## 2026-08-09

- Completed Phase 7B/7B.1 class-wise ByteTrack and generic-luggage tracking output.
- Completed Phase 7C offline candidate-only abandoned-object reasoning and regression tests.

## 2026-08-08

- Completed Phase 7A person/luggage fine-tuning and evaluation.

## 2026-08-07

- Completed DEIMv2 Phase 5 tiled-inference evaluation and the Phase 6 controlled comparison work.

## 2026-08-06

- Completed custom COCO validation, taxonomy preservation, checkpoint initialization, and DEIMv2 smoke-training preparation.
