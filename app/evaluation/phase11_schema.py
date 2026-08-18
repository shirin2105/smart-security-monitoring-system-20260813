"""Phase 11 benchmark schemas and error taxonomy.

Reuses the Phase 8 event types but adds the Phase 11 evaluation fields
(``trigger_time_s`` in GT, canonical ``cv-event-v1`` prediction ingestion and
lifecycle collapse) and the Phase 11 error taxonomy.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from math import isfinite
from typing import Any, Iterable, Mapping
from pathlib import Path

VALID_EVENT_TYPES = {"ZONE_INTRUSION", "CROWD_THRESHOLD", "ABANDONED_OBJECT"}

# Phase 11 error taxonomy (superset of the Phase 8 categories).
PRIMARY_CAUSES = {
    "DETECTOR_MISS",
    "DETECTOR_FALSE_POSITIVE",
    "TRACK_ID_SWITCH",
    "TRACK_FRAGMENTATION",
    "PHYSICAL_STITCH_ERROR",
    "STATIONARY_LOGIC_ERROR",
    "OWNER_ASSOCIATION_ERROR",
    "OWNER_AWAY_LOGIC_ERROR",
    "ROI_ERROR",
    "CROWD_COUNT_ERROR",
    "TIMING_ERROR",
    "DUPLICATE_EVENT",
    "STREAM_RUNTIME_ERROR",
    "UNKNOWN",
}

ERROR_KINDS = {"FP", "FN", "EARLY_ALERT", "LATE_ALERT", "DUPLICATE"}

DEFAULT_TOLERANCES_S = {
    "ZONE_INTRUSION": 2.0,
    "CROWD_THRESHOLD": 3.0,
    "ABANDONED_OBJECT": 5.0,
}

# Lifecycle states collapsed into a single prediction instance.
START = "START"
UPDATE = "UPDATE"
END = "END"


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
        if not (self.clip_id and self.camera_id and self.event_id):
            raise ValueError("clip_id, camera_id, event_id are required")
        if self.event_type not in VALID_EVENT_TYPES:
            raise ValueError(f"unsupported event_type={self.event_type}")
        for name in ("start_s", "trigger_time_s", "end_s"):
            value = float(getattr(self, name))
            if not isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")
        if not self.start_s <= self.trigger_time_s <= self.end_s:
            raise ValueError("trigger_time_s must lie in [start_s, end_s]")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PredictedEvent:
    """A collapsed prediction instance (one per lifecycle)."""

    clip_id: str
    camera_id: str
    event_id: str
    event_type: str
    event_time_s: float
    start_s: float | None = None
    end_s: float | None = None
    confidence: float | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    lifecycle_states: tuple[str, ...] = field(default_factory=tuple)

    def validate(self) -> None:
        if not (self.clip_id and self.camera_id and self.event_id):
            raise ValueError("clip_id, camera_id, event_id are required")
        if self.event_type not in VALID_EVENT_TYPES:
            raise ValueError(f"unsupported event_type={self.event_type}")
        if not isfinite(self.event_time_s) or self.event_time_s < 0:
            raise ValueError("event_time_s must be finite and non-negative")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def ground_truth_from_mapping(payload: Mapping[str, Any]) -> GroundTruthEvent:
    event = GroundTruthEvent(**dict(payload))
    event.validate()
    return event


def load_ground_truth(path: str | Path) -> list[GroundTruthEvent]:
    """Load event-level ground truth from a JSONL file."""
    rows: list[GroundTruthEvent] = []
    seen: set[tuple[str, str, str]] = set()
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            event = ground_truth_from_mapping(payload)
            key = (event.clip_id, event.camera_id, event.event_id)
            if key in seen:
                raise ValueError(f"duplicate GT event identity at line {line_number}: {key}")
            seen.add(key)
            rows.append(event)
    return rows


def prediction_from_cv_event(payload: Mapping[str, Any]) -> PredictedEvent:
    """Convert one canonical ``cv-event-v1`` record into a prediction instance.

    Only START records represent an alert; UPDATE/END extend the same instance.
    Callers collapse a lifecycle group (same event_id) before building one
    PredictedEvent.
    """
    if payload.get("schema_version") != "cv-event-v1":
        raise ValueError(f"unsupported schema_version={payload.get('schema_version')!r}")
    event_type = payload.get("event_type")
    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(f"unsupported event_type={event_type!r}")
    return PredictedEvent(
        clip_id=str(payload["clip_id"]) if "clip_id" in payload else _infer_clip(payload),
        camera_id=str(payload["camera_id"]),
        event_id=str(payload["event_id"]),
        event_type=event_type,
        event_time_s=float(payload["event_time_s"]),
        start_s=_opt_float(payload.get("event_start_s")),
        end_s=_opt_float(payload.get("event_end_s")),
        confidence=_opt_float(payload.get("cv_confidence")),
        evidence=dict(payload.get("evidence") or {}),
        lifecycle_states=(str(payload["event_state"]),),
    )


def _opt_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _infer_clip(payload: Mapping[str, Any]) -> str:
    """Fall back to camera_id when a cv-event-v1 record lacks clip_id."""
    return str(payload.get("camera_id", "UNKNOWN"))


def collapse_lifecycles(predictions: Iterable[PredictedEvent]) -> list[PredictedEvent]:
    """Collapse one lifecycle (START/UPDATE/END, same event_id) into one instance.

    The alert time is the START time; the instance records every lifecycle state
    seen so duplicate/UPDATE accounting is correct.
    """
    groups: dict[str, PredictedEvent] = {}
    for prediction in predictions:
        key = (prediction.clip_id, prediction.camera_id, prediction.event_id)
        existing = groups.get(str(key))
        if existing is None:
            groups[str(key)] = prediction
            continue
        states = (*existing.lifecycle_states, *prediction.lifecycle_states)
        groups[str(key)] = PredictedEvent(
            clip_id=existing.clip_id,
            camera_id=existing.camera_id,
            event_id=existing.event_id,
            event_type=existing.event_type,
            event_time_s=min(existing.event_time_s, prediction.event_time_s),
            start_s=existing.start_s if existing.start_s is not None else prediction.start_s,
            end_s=prediction.end_s if prediction.end_s is not None else existing.end_s,
            confidence=existing.confidence if existing.confidence is not None else prediction.confidence,
            evidence=existing.evidence or prediction.evidence,
            lifecycle_states=states,
        )
    return list(groups.values())
