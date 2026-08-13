from __future__ import annotations

from collections import defaultdict
from math import hypot
from typing import Iterable, Sequence

from .jsonl_loader import TrackPoint


def group_trajectories(points: Iterable[TrackPoint]) -> dict[int, list[TrackPoint]]:
    grouped: dict[int, list[TrackPoint]] = defaultdict(list)
    for point in points:
        grouped[point.global_track_id].append(point)
    return {
        track_id: sorted(items, key=lambda item: (item.timestamp_s, item.frame_index))
        for track_id, items in grouped.items()
    }


def displacement_px(points: Sequence[TrackPoint]) -> float:
    """Straight-line center displacement between the first and last observation."""
    if len(points) < 2:
        return 0.0
    start, end = points[0].center_xy, points[-1].center_xy
    return hypot(end[0] - start[0], end[1] - start[1])


def normalized_displacement(points: Sequence[TrackPoint], reference_size_px: float) -> float:
    if reference_size_px <= 0:
        raise ValueError("reference_size_px must be positive")
    return displacement_px(points) / reference_size_px
