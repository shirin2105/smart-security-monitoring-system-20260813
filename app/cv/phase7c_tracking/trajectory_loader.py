from __future__ import annotations

from pathlib import Path

from .jsonl_loader import TrackPoint, load_track_jsonl
from .trajectory import group_trajectories


def load_trajectories(path: str | Path) -> dict[int, list[TrackPoint]]:
    """Load Phase 7B or generic-luggage Phase 7B.1 JSONL by global track ID."""
    return group_trajectories(load_track_jsonl(path))
