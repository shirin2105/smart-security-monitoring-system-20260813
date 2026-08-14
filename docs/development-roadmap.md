# Development Roadmap

## Current status

| Capability | Status | Evidence |
|---|---|---|
| Phase 9 unified CV worker | Complete | DEIMv2 -> ByteTrack -> shared TrackStore -> three adapters -> CVEventManager |
| CVEvent v1 publisher boundary | Complete | `CVEventPublisher.publish(CVEvent)` with canonical local `JsonlPublisher`; backend endpoint not required |
| Phase 9 real-video regression | Complete | ABODA, intrusion, crowd, and negative clips passed; valid lifecycle JSONL without duplicate payloads |
| Phase 9 CV tests | Complete | 78 tests plus 8 subtests passed; webcam devtool tests 3/3 passed |
| Webcam code | Ready; user manual verification | Agent environment did not claim hardware PASS |
| Class-independent static-region candidates | Legacy | Retained historical experiment; not active in unified worker |
| Deterministic media timestamps | Complete | Fixed source epoch and frame-offset tests |
| Hugging Face / temporal VLM validation | Legacy | Outside active Phase 9; retained only where tests or historical demos still import it |
| Six-camera bounded supervisor | Complete | Shared-detector and failure-isolation unit test |
| DEIMv2 Phase 7A production runtime | Complete | Active shared detector, class-isolated ByteTrack, mandatory artifact hashes, full test suite, and real-asset CPU smoke |
| Canonical PETS real-data demo | Complete | Video plus machine-readable summary artifact |
| Authenticated PETS temporal VLM demo | Complete | 16-frame Gemma request rejected one false-person candidate at 0.99; no alert |
| DEIMv2 generic-luggage evaluation runtime | Complete, visual review pending | Phase 7B.1 Kaggle run completed over 2,189 frames at 20.10 FPS, produced 17 tracks and 5,019 valid JSONL observations, and removed 60.48% of duplicate luggage-class boxes. Zero background anchors were learned, so suppression quality remains unverified. See [`reports/deimv2_phase7b1_generic_luggage_report.md`](../reports/deimv2_phase7b1_generic_luggage_report.md). |
| Real six-camera performance benchmark | Not started | No benchmark or production camera result exists |
| Static-region quality evaluation | Not started | Demo output is not a labeled accuracy evaluation |

## Next priorities

1. User hardware-verifies webcam: intrusion on the right half, crowd with two people, and Phase7C abandoned object.
2. Benchmark one through six real streams on declared hardware; report throughput, latency, memory, dropped frames, and detector-lock contention.
3. Build a labeled evaluation set for the three active event types and tune Phase7C owner/stationary thresholds from measured results.

## Acceptance evidence

Phase 9 CV tests passed 78 tests plus 8 subtests; webcam devtool tests passed 3/3.
Real-video production regression
passed four clips and persisted only schema-valid CVEvent v1 JSONL records. Full-repo
collection is classified as environment/optional dependency missing because the
lightweight CV environment lacks backend/agent packages such as `langgraph`,
`fastapi`, and `websockets`; this is not a Phase 9 CV test failure. Webcam hardware
verification remains user manual. See
[`phase9-real-video-regression.md`](../reports/phase9-real-video-regression.md).
