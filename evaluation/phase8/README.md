# Phase 8 CV E2E validation

Scope is limited to `ZONE_INTRUSION`, `CROWD_THRESHOLD`, and
`ABANDONED_OBJECT`. The frozen runtime is DEIMv2 Phase 7A, class-wise
ByteTrack, and Phase 7C abandoned-object reasoning. This suite does not train
models and does not introduce S4, EdgeCrafter, YOLO, VLM, backend, or UI work.

## Required inputs

- One manifest containing 20–30 real positive and negative clips.
- A camera configuration for every clip.
- Human-labeled `ground_truth_events.jsonl` with `trigger_time_s`.
- Frozen Phase 7A checkpoint and Phase 7B.1 tracker runtime.

The included manifest is smoke-only. Production validation fails closed when
the clip count is outside 20–30 or when positive/negative scenarios are absent.

## Commands

Validate configuration:

```powershell
python tools/phase8/validate_config.py --manifest evaluation/phase8/manifest.json
```

Run one clip using an existing Phase 7B.1 track file:

```powershell
python tools/phase8/inference_video.py --video clip.mp4 --camera-id CAM_01 `
  --camera-config configs/phase8_camera.example.json --tracks tracks_v4.jsonl `
  --out pred_events.jsonl
```

Run the batch:

```powershell
python tools/phase8/phase8_batch_runner.py --manifest evaluation/phase8/manifest.json `
  --out-root artifacts/phase8-predictions --infer-cmd-template `
  "python tools/phase8/inference_video.py --video {video_path} --clip-id {clip_id} --camera-id {camera_id} --camera-config {camera_config_path} --out {pred_path} --work-dir {clip_out_dir}"
```

Evaluate and generate the attribution worksheet/report:

```powershell
python tools/phase8/evaluate_events.py --manifest evaluation/phase8/manifest.json `
  --gt evaluation/phase8/ground_truth_events.jsonl `
  --pred artifacts/phase8-predictions/predictions_all.jsonl `
  --attributions evaluation/phase8/error_attribution.csv `
  --out-dir reports/phase8
```

Every unmatched FP/FN is written to `error_attribution.csv`. `UNKNOWN` is a
valid temporary category but blocks model-change decisions until video review.

Phase 7C remains candidate-only. For `ABANDONED_OBJECT`, Phase 8 reports
candidate precision/recall/F1 and false candidates/hour; it does not relabel a
candidate as a confirmed alarm. Intrusion and crowd retain alert-level false
alarms/hour.

## Unresolved questions

- Which Kaggle Dataset contains the finalized 20–30 labeled clips?
- Threshold review waits for the completed prediction batch and video evidence.
