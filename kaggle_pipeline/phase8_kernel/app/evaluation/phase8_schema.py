from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import isfinite
from typing import Any, Mapping


VALID_EVENT_TYPES = {
    "ZONE_INTRUSION",
    "CROWD_THRESHOLD",
    "ABANDONED_OBJECT",
}
ERROR_CATEGORIES = {
    "DETECTOR_MISS",
    "DETECTOR_FALSE_POSITIVE",
    "TRACK_ID_SWITCH",
    "TRACK_FRAGMENTATION",
    "PHYSICAL_STITCH_ERROR",
    "STATIONARY_LOGIC_ERROR",
    "OWNER_ASSOCIATION_ERROR",
    "OWNER_AWAY_LOGIC_ERROR",
    "ROI_ERROR",
    "DUPLICATE_EVENT",
    "TIMING_ERROR",
    "UNKNOWN",
}


def _finite_non_negative(name: str, value: float) -> None:
    if not isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and non-negative")


@dataclass(frozen=True)
class GroundTruthEvent:
    clip_id: str
    camera_id: str
    event_id: str
    event_type: str
    start_s: float
    trigger_time_s: float
    end_s: float
    zone_id: str | None = None
    notes: str | None = None

    def validate(self) -> None:
        _validate_identity(self.clip_id, self.camera_id, self.event_id, self.event_type)
        for name in ("start_s", "trigger_time_s", "end_s"):
            _finite_non_negative(name, float(getattr(self, name)))
        if not self.start_s <= self.trigger_time_s <= self.end_s:
            raise ValueError("trigger_time_s must be inside [start_s, end_s]")


@dataclass(frozen=True)
class PredictedEvent:
    clip_id: str
    camera_id: str
    event_id: str
    event_type: str
    event_time_s: float
    start_s: float | None = None
    end_s: float | None = None
    confidence: float | None = None
    evidence: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        _validate_identity(self.clip_id, self.camera_id, self.event_id, self.event_type)
        _finite_non_negative("event_time_s", float(self.event_time_s))
        if self.start_s is not None:
            _finite_non_negative("start_s", float(self.start_s))
        if self.end_s is not None:
            _finite_non_negative("end_s", float(self.end_s))
        if self.start_s is not None and self.end_s is not None and self.end_s < self.start_s:
            raise ValueError("end_s must be >= start_s")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be in [0, 1]")
        if not isinstance(self.evidence, dict):
            raise ValueError("evidence must be an object")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _validate_identity(clip_id: str, camera_id: str, event_id: str, event_type: str) -> None:
    if not clip_id or not camera_id or not event_id:
        raise ValueError("clip_id, camera_id and event_id are required")
    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(f"unsupported event_type={event_type}")


def ground_truth_from_mapping(payload: Mapping[str, Any]) -> GroundTruthEvent:
    event = GroundTruthEvent(**dict(payload))
    event.validate()
    return event


def prediction_from_mapping(payload: Mapping[str, Any]) -> PredictedEvent:
    event = PredictedEvent(**dict(payload))
    event.validate()
    return event
