from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .jsonl_loader import TrackPoint
from .trajectory import displacement_px, normalized_displacement


@dataclass(frozen=True)
class StationaryFeatureConfig:
    """Feature configuration only; decision thresholds remain intentionally unset."""

    reference_size_px: float
    stationary_displacement_threshold: float | None = None
    stationary_duration_threshold_s: float | None = None

    def __post_init__(self) -> None:
        if self.reference_size_px <= 0:
            raise ValueError("reference_size_px must be positive")
        if self.stationary_displacement_threshold is not None:
            raise ValueError("stationary threshold tuning is outside this skeleton")
        if self.stationary_duration_threshold_s is not None:
            raise ValueError("stationary duration tuning is outside this skeleton")


@dataclass(frozen=True)
class ObjectMotionState:
    global_track_id: int
    stationary_score: float | None
    stationary_since: float | None
    displacement_px: float
    displacement_normalized: float


class StationaryFeatureExtractor:
    """Extract motion features without classifying a track as stationary."""

    def __init__(self, config: StationaryFeatureConfig):
        self.config = config

    def extract(self, points: Sequence[TrackPoint]) -> ObjectMotionState:
        if not points:
            raise ValueError("at least one track point is required")
        track_ids = {point.global_track_id for point in points}
        if len(track_ids) != 1:
            raise ValueError("all points must belong to one global track")
        pixels = displacement_px(points)
        normalized = normalized_displacement(points, self.config.reference_size_px)
        return ObjectMotionState(
            global_track_id=points[0].global_track_id,
            stationary_score=None,
            stationary_since=None,
            displacement_px=pixels,
            displacement_normalized=normalized,
        )
