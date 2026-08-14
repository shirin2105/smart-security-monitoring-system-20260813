from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ObjectMotionState:
    luggage_track_id: int
    displacement_normalized: float
    stationary_score: float | None
    stationary_since: float | None


@dataclass(frozen=True)
class OwnerAssociationState:
    luggage_track_id: int
    person_track_id: int | None
    association_score: float | None
    last_near_timestamp: float | None
