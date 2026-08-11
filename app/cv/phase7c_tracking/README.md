# Phase 7C tracking feature skeleton

This package consumes `tracks.jsonl` from the Phase 7B class-wise ByteTrack runner.
It also accepts `tracks_v4.jsonl` from the Phase 7B.1 generic-luggage runtime.
It deliberately stops before abandoned-object decisions.

## Included

- streaming JSONL validation via `load_track_jsonl`;
- trajectory grouping and pixel/normalized displacement;
- `StationaryFeatureExtractor`, which returns raw motion features only;
- `OwnerAssociation` result contract and `OwnerAssociator` strategy protocol.
- `load_trajectories` and `extract_stationary_features` adapters for generic luggage.

## Example

```python
from app.cv.phase7c_tracking import (
    StationaryFeatureConfig,
    StationaryFeatureExtractor,
    group_trajectories,
    load_track_jsonl,
)

tracks = group_trajectories(load_track_jsonl("tracks.jsonl"))
extractor = StationaryFeatureExtractor(
    StationaryFeatureConfig(reference_size_px=1920.0)
)
features = [extractor.extract(points) for points in tracks.values()]
```

`reference_size_px` must be supplied from the camera/frame geometry. Stationary and
owner-away thresholds are intentionally unset. This package does not emit
`ABANDONED_OBJECT_CANDIDATE` or any other event.

## Phase 7C v1 offline replay

The full offline reasoning engine lives in
`kaggle_pipeline/phase7c_kernel/phase7c_core.py`. It consumes the Phase 7B.1
`tracks_v4.jsonl`; it does not run the detector or train a model.

```powershell
python tools/phase7c/replay_phase7c.py `
  --tracks artifacts/phase7b1-results/phase7b1_generic_luggage/tracks_v4.jsonl `
  --video kaggle_pipeline/phase7b_video_dataset/aboda-video1.avi `
  --config configs/phase7c_cameras.example.json `
  --camera-id aboda_camera_01 `
  --output-dir artifacts/phase7c-local
```

The output contains quality, physical-luggage, owner, event, timeline and
optional annotated-video artifacts. Event rows are validated by
`AbandonedObjectCandidate` and remain HITL/backend candidates only; they are
not confirmed alarms.

Evaluate against an independently authored label manifest:

```powershell
python tools/evaluation/evaluate_phase7c_events.py `
  --events artifacts/phase7c-local/phase7c_events.json `
  --manifest evaluation/phase7c_manifest.json `
  --output reports/phase7c_metrics.json
```

Do not tune the baseline thresholds from the ABODA clip alone. Review the
annotated video, then add negative clips before any per-camera tuning.
