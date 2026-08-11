from __future__ import annotations

from typing import Sequence

from .jsonl_loader import TrackPoint
from .phase7c_types import ObjectMotionState
from .trajectory import normalized_displacement


def extract_stationary_features(
    trajectory: Sequence[TrackPoint],
    reference_size_px: float,
) -> ObjectMotionState:
    """Return motion evidence only; no final stationary threshold is applied."""
    if not trajectory:
        raise ValueError("trajectory must not be empty")
    track_ids = {point.global_track_id for point in trajectory}
    if len(track_ids) != 1:
        raise ValueError("trajectory must contain exactly one track")
    if any(point.class_name not in {"luggage", "backpack", "handbag", "suitcase"} for point in trajectory):
        raise ValueError("stationary luggage features require a luggage trajectory")
    return ObjectMotionState(
        luggage_track_id=trajectory[0].global_track_id,
        displacement_normalized=normalized_displacement(
            trajectory, reference_size_px=reference_size_px
        ),
        stationary_score=None,
        stationary_since=None,
    )
