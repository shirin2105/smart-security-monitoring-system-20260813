from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.cv.contracts.validation import EVENT_TYPES


@dataclass(frozen=True, slots=True)
class EventSignal:
    """Internal engine fact; lifecycle state and IDs belong to CVEventManager."""

    camera_id: str
    event_type: str
    entity_key: str
    active: bool
    event_time: str
    event_time_s: float
    cv_confidence: float
    objects: dict[str, Any]
    evidence: dict[str, Any]
    spatial: dict[str, Any] = field(default_factory=dict)
    media: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.event_type not in EVENT_TYPES:
            raise ValueError(f"unsupported CV event type: {self.event_type}")
        if not self.camera_id or not self.entity_key:
            raise ValueError("camera_id and entity_key must be non-empty")
        if self.event_time_s < 0:
            raise ValueError("event_time_s must be non-negative")
        if not 0 <= self.cv_confidence <= 1:
            raise ValueError("cv_confidence must be within [0, 1]")

    @property
    def key(self) -> tuple[str, str, str]:
        return self.camera_id, self.event_type, self.entity_key
