from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Literal, Mapping


@dataclass(frozen=True)
class AbandonedObjectCandidate:
    """Backend/HITL candidate evidence; this is never a confirmed alarm."""

    event_id: str
    physical_id: str
    source_track_ids: tuple[int, ...]
    owner_person_track_id: int
    stationary_start_s: float
    stationary_confirmed_s: float
    owner_last_near_s: float
    candidate_time_s: float
    owner_away_s: float
    association_score: float
    bbox_xyxy: tuple[float, float, float, float]
    center_xy: tuple[float, float]
    status: Literal["ABANDONED_OBJECT_CANDIDATE"] = "ABANDONED_OBJECT_CANDIDATE"

    def __post_init__(self) -> None:
        if not self.event_id or not self.physical_id:
            raise ValueError("event_id and physical_id are required")
        if not self.source_track_ids or any(track_id < 0 for track_id in self.source_track_ids):
            raise ValueError("source_track_ids must contain non-negative IDs")
        if self.owner_person_track_id < 0:
            raise ValueError("owner_person_track_id must be non-negative")
        numeric = (
            self.stationary_start_s,
            self.stationary_confirmed_s,
            self.owner_last_near_s,
            self.candidate_time_s,
            self.owner_away_s,
            self.association_score,
            *self.bbox_xyxy,
            *self.center_xy,
        )
        if not all(isfinite(value) for value in numeric):
            raise ValueError("candidate numeric fields must be finite")
        if not (
            self.stationary_start_s
            <= self.stationary_confirmed_s
            <= self.candidate_time_s
        ):
            raise ValueError("stationary timestamps are out of order")
        if self.owner_last_near_s > self.candidate_time_s or self.owner_away_s < 0:
            raise ValueError("owner-away timestamps are inconsistent")
        if abs(
            self.owner_away_s
            - (self.candidate_time_s - self.owner_last_near_s)
        ) > 1e-6:
            raise ValueError("owner_away_s must match candidate_time_s - owner_last_near_s")
        if not 0.0 <= self.association_score <= 1.0:
            raise ValueError("association_score must be in [0, 1]")
        x1, y1, x2, y2 = self.bbox_xyxy
        if x2 <= x1 or y2 <= y1:
            raise ValueError("bbox_xyxy must have positive width and height")
        if self.status != "ABANDONED_OBJECT_CANDIDATE":
            raise ValueError("Phase 7C may emit candidates only")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "AbandonedObjectCandidate":
        expected = {
            "event_id",
            "physical_id",
            "source_track_ids",
            "owner_person_track_id",
            "stationary_start_s",
            "stationary_confirmed_s",
            "owner_last_near_s",
            "candidate_time_s",
            "owner_away_s",
            "association_score",
            "bbox_xyxy",
            "center_xy",
            "status",
        }
        extra = set(payload) - expected
        if extra:
            raise ValueError(f"unexpected candidate fields: {sorted(extra)}")
        return cls(
            event_id=str(payload["event_id"]),
            physical_id=str(payload["physical_id"]),
            source_track_ids=tuple(int(value) for value in payload["source_track_ids"]),
            owner_person_track_id=int(payload["owner_person_track_id"]),
            stationary_start_s=float(payload["stationary_start_s"]),
            stationary_confirmed_s=float(payload["stationary_confirmed_s"]),
            owner_last_near_s=float(payload["owner_last_near_s"]),
            candidate_time_s=float(payload["candidate_time_s"]),
            owner_away_s=float(payload["owner_away_s"]),
            association_score=float(payload["association_score"]),
            bbox_xyxy=tuple(float(value) for value in payload["bbox_xyxy"]),
            center_xy=tuple(float(value) for value in payload["center_xy"]),
            status=str(payload.get("status", "ABANDONED_OBJECT_CANDIDATE")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "physical_id": self.physical_id,
            "source_track_ids": list(self.source_track_ids),
            "owner_person_track_id": self.owner_person_track_id,
            "stationary_start_s": self.stationary_start_s,
            "stationary_confirmed_s": self.stationary_confirmed_s,
            "owner_last_near_s": self.owner_last_near_s,
            "candidate_time_s": self.candidate_time_s,
            "owner_away_s": self.owner_away_s,
            "association_score": self.association_score,
            "bbox_xyxy": list(self.bbox_xyxy),
            "center_xy": list(self.center_xy),
            "status": self.status,
        }
