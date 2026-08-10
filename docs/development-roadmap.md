# Development Roadmap

## Current status

| Capability | Status | Evidence |
|---|---|---|
| Class-independent static-region candidates | Complete | Detector, engine route, unit and integration tests |
| Deterministic media timestamps | Complete | Fixed source epoch and frame-offset tests |
| Production Hugging Face multimodal validation | Complete | Enabled by default with Gemma 3 4B; environment-only token, no-startup-network, missing-token, request/response, and malformed-response tests |
| Temporal full-scene VLM validation | Complete | Default 1 FPS `T-8s..T+8s` buffering, +8-second deferred decision, fail-open unavailable result, original timestamp, memory/request bounds, and EOS tests |
| Six-camera bounded supervisor | Complete | Shared-detector and failure-isolation unit test |
| Canonical PETS real-data demo | Complete | Video plus machine-readable summary artifact |
| Authenticated PETS temporal VLM demo | Complete | 16-frame Gemma request rejected one false-person candidate at 0.99; no alert |
| DEIMv2 generic-luggage tracking runtime | Complete, visual review pending | Phase 7B.1 Kaggle run completed over 2,189 frames at 20.10 FPS, produced 17 tracks and 5,019 valid JSONL observations, and removed 60.48% of duplicate luggage-class boxes. Zero background anchors were learned, so suppression quality remains unverified. See [`reports/deimv2_phase7b1_generic_luggage_report.md`](../reports/deimv2_phase7b1_generic_luggage_report.md). |
| Real six-camera performance benchmark | Not started | No benchmark or production camera result exists |
| Static-region quality evaluation | Not started | Demo output is not a labeled accuracy evaluation |

## Next priorities

1. Build a labeled evaluation set for static-region precision, recall, time-to-alert, and region fragmentation.
2. Benchmark one through six real streams on declared hardware; report throughput, latency, memory, dropped frames, and detector-lock contention.
3. Evaluate temporal Hugging Face validation on a labeled multi-scene dataset; the single authenticated PETS decision proves execution, not accuracy.
4. Tune static-region and owner-association settings per camera scene using measured results.

## Acceptance evidence

The completed milestone is supported by focused tests under `tests/unit/`, `tests/integration/test_static_abandoned_pipeline.py`, and `tests/integration/test_temporal_full_frame_vlm_pipeline.py`, plus the reproducible command and artifacts documented in [`system-architecture.md`](./system-architecture.md). The authenticated PETS run rejected one false-person candidate using 16 full-scene frames and emitted no alert; the detector/heuristic comparison emitted three alerts, first at 45.5 seconds. Completion means the implemented contracts work; it does not establish production accuracy, scale, or six-camera performance.
