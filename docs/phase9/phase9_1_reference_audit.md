# Phase 9.1 reference audit

| Reference family | Classification | Disposition |
|---|---|---|
| DEIMv2, ByteTrack, TrackStore, Phase7C, CVEvent v1, JsonlPublisher | ACTIVE_RUNTIME | Canonical CV path. |
| `configs/event_rules.yaml` Phase7C tree | ACTIVE_CONFIG | Validated thresholds retained unchanged. |
| `app/vlm`, `app/cv/static_region_detector.py`, `app/events/abandoned_object.py` | LEGACY/HISTORICAL | Still imported by legacy demos/tests; no production worker import. Retain isolated. |
| static-region/VLM tests and `scripts/generate_static_abandoned_demo.py` | LEGACY/HISTORICAL | Preserve as historical experiment coverage. |
| `EventCandidate` backend publisher/API/agent modules | COMPATIBILITY_OUT_OF_SCOPE | Backend/LLM boundary; not canonical CV output. |
| YOLO/Ultralytics/StrongSORT references in historical docs/scripts | LEGACY/HISTORICAL | Not an active detector/tracker route. |

Production import audit: `app/cv/worker.py`, adapters, detector, tracker and publishers
contain zero `app.vlm` import and zero `StaticRegionDetector` usage. No deletion is safe
while the retained historical scripts and focused legacy tests import these modules.

## Final closure — 2026-08-14

The final grep covered `app.vlm`, `VLM`, `StaticRegionDetector`,
`candidate_source`, `static_regions`, `YOLO`, `yolo26m`, `ultralytics`,
`StrongSORT`, and `EventCandidate`, excluding only Git metadata, disposable virtual
environments, and the checked-out DEIMv2 third-party source. No hit is an active
dependency of the unified CV worker.

| Remaining location family | Classification | Reason |
|---|---|---|
| `app/cv/worker.py` legacy-key warning; `app/cv/demo_flow.py` legacy preflight | LEGACY | Guards reject or ignore old static-region/VLM configuration; neither imports the old runtime. |
| `app/cv/static_region_detector.py`, `app/vlm/**`, `app/events/abandoned_object.py`, `scripts/generate_static_abandoned_demo.py` | LEGACY | Isolated experiment surface retained because its legacy tests/demo still import it. |
| `tests/unit/test_region_validator.py`, `tests/unit/test_static_region_detector.py`, `tests/unit/test_static_region_contracts.py`, `tests/unit/test_abandoned_object.py`, `tests/unit/test_temporal_full_frame_boundaries.py`, `tests/integration/test_production_vlm_configuration.py`, `tests/integration/test_static_abandoned_demo_decisions.py`, `tests/integration/test_static_abandoned_pipeline.py`, `tests/integration/test_temporal_full_frame_vlm_pipeline.py` | TEST | Tests for the isolated historical surface; not run by the unified worker. |
| `app/publisher/{base,http_publisher,local_json_publisher}.py`, `app/events/**`, `app/services/intake.py`, `app/api/events.py`, `app/agents/**`, `back-end/app/api/events_ingest.py`, `back-end/tests/test_api.py`, and their tests | ACTIVE_RUNTIME / ACTIVE_CONFIG | Backend/agent compatibility uses `EventCandidate`; it is outside the final CVEvent v1 boundary and is not a CV worker dependency. |
| `README.md`, `docs/architecture/current_cv_runtime.md`, `docs/system-architecture.md`, `reports/phase9-final-report.md` | CURRENT_DOC | All current references label the non-canonical path as legacy or compatibility-only. |
| `docs/journals/**`, `docs/project-changelog.md`, `docs/{README,SPEC,PRD,BRD,BRIEF,ARCHITECTURE}.md`, `plans/**`, `plans/reports/**`, `reports/**`, `evaluation/phase8/README.md`, `kaggle_pipeline/**` | HISTORICAL | Historical experiments, completed plans, evaluation material, or separately scoped Phase 8 material. |
| `artifacts/**`, `datasets/mock_cv_output_candidates.json`, `repomix-output.xml` | HISTORICAL | Generated experiment evidence, fixture data, or a generated repository snapshot. |

The canonical stack is verified by `app/cv/worker.py` and the focused tests: DEIMv2,
ByteTrack, one shared TrackStore, Intrusion/Crowd/Phase7C Abandoned adapters,
CVEvent v1, and JsonlPublisher. YOLO/Ultralytics, StrongSORT, VLM/Gemma, and
static-region terms that remain in current architecture documentation are explicitly
marked **LEGACY**.
