from typing import Any, Dict, List, Optional, Tuple

from app.common.geometry import get_foot_point
from app.common.schemas import TrackResult


class TrackState:
    def __init__(self, track_id: int, class_name: str, bbox: List[float], confidence: float, timestamp: str):
        self.track_id = track_id
        self.class_name = class_name
        self.bbox_history: List[List[float]] = [bbox]
        self.foot_points: List[Tuple[float, float]] = [get_foot_point(bbox)]
        self.confidence = confidence
        self.first_seen_at = timestamp
        self.last_seen_at = timestamp
        self.current_zone: Optional[str] = None
        self.entered_zone_at: Optional[str] = None
        self.stationary_since: Optional[str] = None
        self.owner_candidate_track_id: Optional[int] = None
        self.created_events: Dict[str, Any] = {}

    def update(self, bbox: List[float], confidence: float, timestamp: str) -> None:
        self.bbox_history.append(bbox)
        self.foot_points.append(get_foot_point(bbox))
        self.confidence = confidence
        self.last_seen_at = timestamp

    @property
    def latest_bbox(self) -> List[float]:
        return self.bbox_history[-1]

    @property
    def latest_foot_point(self) -> Tuple[float, float]:
        return self.foot_points[-1]


class TrackStore:
    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        self.tracks: Dict[int, TrackState] = {}

    def update_track(self, track_result: TrackResult) -> TrackState:
        t_id = track_result.track_id
        if t_id not in self.tracks:
            self.tracks[t_id] = TrackState(
                track_id=t_id,
                class_name=track_result.class_name,
                bbox=track_result.bbox,
                confidence=track_result.confidence,
                timestamp=track_result.last_seen_at,
            )
        else:
            self.tracks[t_id].update(
                bbox=track_result.bbox,
                confidence=track_result.confidence,
                timestamp=track_result.last_seen_at,
            )
        return self.tracks[t_id]

    def get_track(self, track_id: int) -> Optional[TrackState]:
        return self.tracks.get(track_id)

    def get_active_tracks(self) -> List[TrackState]:
        return list(self.tracks.values())

    def reset(self) -> None:
        """Discard camera-local state after a continuity-breaking source outage."""
        self.tracks.clear()
