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
