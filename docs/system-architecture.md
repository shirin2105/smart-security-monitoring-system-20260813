# System Architecture

## Current CV pipeline

The active branch is CV-only:

1. DEIMv2-S detects `person`, `backpack`, `handbag`, and `suitcase` using the Phase 7A checkpoint.
2. Class-wise ByteTrack assigns stable track identities.
3. Deterministic rule engines produce zone-intrusion and crowd candidates.
4. Phase 7C trajectory, stationary, and owner-association logic produces candidate-only abandoned-object events.
5. The `cv-event-v1` contract serializes `START`, `UPDATE`, and `END` lifecycle records as JSON/JSONL for the next system layer.

YOLO and multimodal-model inference are not dependencies of this branch. Their last maintained state is preserved on the `legacy-yolo` branch.

## Taxonomy

The detector retains the locked four-class Phase 7A taxonomy:

- `person`
- `backpack`
- `handbag`
- `suitcase`

The Phase 7C abandoned-object result remains `ABANDONED_OBJECT_CANDIDATE`; it is not promoted to a confirmed alarm inside the CV layer.

## Runtime boundaries

- `app/cv/phase7c_tracking/`: trajectory loading, stationary features, physical-luggage stitching, and owner association.
- `app/cv/phase8_event_adapter.py`: thin adapter for intrusion, crowd, and candidate-only abandoned events.
- `app/cv/contracts/`: stable `cv-event-v1` handoff contract and JSONL IO.
- `app/evaluation/`: Phase 7C/8 metrics and validation helpers.
- `tools/phase7c/` and `tools/phase8/`: replay, batch inference, validation, and evaluation CLIs.
- `devtools/webcam_cv_test/`: local DEIMv2/ByteTrack webcam verification only.
- `kaggle_pipeline/`: isolated training/evaluation runners and reproducible Kaggle packaging.

## Model provenance

The main detector lineage is DEIMv2-S initialized from COCO and fine-tuned on the locked VisDrone/person-luggage taxonomy. Phase 5 established the tiled-inference accuracy/latency trade-off. Phase 7A produced the person/luggage checkpoint used by tracking and later event validation.

No training occurs in Phase 7B, Phase 7C, Phase 8, Phase 8.5, or Phase 8.9.

## Validation boundary

Phase 8 evaluates event precision, recall, F1, false candidates per video hour, and detection delay on a fixed CAVIAR validation set. False positives and false negatives require explicit attribution. Candidate-only abandoned-object metrics must not be presented as confirmed-alert metrics.

## API boundary

`app/main.py` exposes health, debug, and internal event-ingestion routes. It does not start a detector, webcam, or semantic model automatically. CV events should be handed off through `cv-event-v1`; downstream policy, alerting, LLM, and backend decisions are out of scope for this branch.
