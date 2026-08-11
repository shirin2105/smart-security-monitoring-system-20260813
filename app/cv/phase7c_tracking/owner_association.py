from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence, runtime_checkable

from .jsonl_loader import TrackPoint


@dataclass(frozen=True)
class OwnerAssociation:
    luggage_track_id: int
    person_track_id: int | None
    association_score: float | None
    last_near_timestamp: float | None


OwnerAssociationResult = OwnerAssociation


@runtime_checkable
class OwnerAssociator(Protocol):
    """Contract for a future owner model; no owner-away decision is made here."""

    def associate(
        self,
        luggage_trajectory: Sequence[TrackPoint],
        person_trajectories: Sequence[Sequence[TrackPoint]],
    ) -> OwnerAssociation:
        ...
