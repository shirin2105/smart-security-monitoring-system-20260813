# Development Roadmap

| Milestone | Status | Evidence |
|---|---|---|
| Custom VisDrone COCO validation | Complete | Ten classes retained; category remapping disabled; split leakage checks and dataset reports added |
| DEIMv2-S initialization and smoke training | Complete | Compatible pretrained weights loaded with explicit classifier reinitialization |
| DEIMv2 tiled inference | Complete | `tile640_overlap25`: AP50:95 0.2744, AP-small 0.1849, AR-small 0.3608 |
| Person/luggage fine-tuning | Complete | Phase 7A four-class checkpoint and six evaluation modes produced |
| Class-wise ByteTrack | Complete | Phase 7B/7B.1 JSONL tracking runtime; visual quality review remains advisable |
| Candidate-only abandoned reasoning | Complete | Phase 7C trajectory, stationary, stitching, owner association, and replay gates |
| Three-event CV E2E validation | In progress | CAVIAR dataset/tooling prepared; final batch result and reviewed FP/FN attribution remain the completion gate |
| Local webcam verification | Complete | DEIMv2/ByteTrack web test plus start/stop launchers |
| CV handoff contract | Complete | `cv-event-v1` envelope, lifecycle, builders, validators, examples, and tests |
| YOLO/multimodal legacy split | Complete | Legacy implementation preserved on `legacy-yolo`; active branch is CV-only |

## Next priorities

1. Complete the 20-clip Phase 8 run and human-review every FP/FN attribution.
2. Review annotated tracking videos before tuning stationary or owner-away thresholds.
3. Benchmark full-frame and tiled modes on target camera hardware.
4. Integrate the stable `cv-event-v1` stream with the next layer without changing CV event semantics.

## Scope constraints

- Do not retrain during validation or tracking phases.
- Do not add S4 or EdgeCrafter without measured error attribution.
- Do not emit a confirmed abandoned-object alarm from candidate-only Phase 7C logic.
- Do not reintroduce YOLO or multimodal inference into the active branch.
