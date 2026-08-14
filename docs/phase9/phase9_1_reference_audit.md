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
