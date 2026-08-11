from __future__ import annotations

import math
from datetime import datetime
from typing import Any

SCHEMA_VERSION = "cv-event-v1"
EVENT_TYPES = {"ZONE_INTRUSION", "CROWD_THRESHOLD", "ABANDONED_OBJECT"}
EVENT_STATES = {"START", "UPDATE", "END"}
FIELDS = {
    "schema_version", "event_id", "event_type", "event_state", "camera_id",
    "event_time", "event_time_s", "cv_confidence", "objects", "evidence",
    "spatial", "media", "diagnostics",
}


class CVEventValidationError(ValueError):
    pass


def _fail(field: str, message: str) -> None:
    raise CVEventValidationError(f"{field}: {message}")


def _number(value: Any, field: str, minimum: float | None = None,
            maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(field, "must be a number")
    value = float(value)
    if not math.isfinite(value):
        _fail(field, "must be finite")
    if minimum is not None and value < minimum:
        _fail(field, f"must be >= {minimum}")
    if maximum is not None and value > maximum:
        _fail(field, f"must be <= {maximum}")
    return value


def _nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(field, "must be a non-empty string")
    return value


def _dict(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(field, "must be an object")
    return value


def _track_id(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(field, "must be an integer")
    if value < 0:
        _fail(field, "must be >= 0")
    return value


def _bbox(value: Any, field: str) -> None:
    if not isinstance(value, list) or len(value) != 4:
        _fail(field, "must contain four coordinates")
    coords = [_number(item, f"{field}[{index}]") for index, item in enumerate(value)]
    if coords[2] < coords[0] or coords[3] < coords[1]:
        _fail(field, "must use ordered xyxy coordinates")


def _validate_intrusion(objects: dict, evidence: dict) -> None:
    persons = objects.get("persons")
    if not isinstance(persons, list) or not persons:
        _fail("objects.persons", "must be a non-empty list")
    for index, person in enumerate(persons):
        person = _dict(person, f"objects.persons[{index}]")
        _track_id(person.get("track_id"), f"objects.persons[{index}].track_id")
        _bbox(person.get("bbox_xyxy"), f"objects.persons[{index}].bbox_xyxy")
    _nonempty(evidence.get("zone_id"), "evidence.zone_id")
    _number(evidence.get("inside_duration_s"), "evidence.inside_duration_s", 0)


def _validate_crowd(objects: dict, evidence: dict) -> None:
    count = _number(objects.get("person_count"), "objects.person_count", 0)
    if not count.is_integer():
        _fail("objects.person_count", "must be an integer")
    track_ids = objects.get("person_track_ids")
    if not isinstance(track_ids, list):
        _fail("objects.person_track_ids", "must be a list")
    for index, track_id in enumerate(track_ids):
        _track_id(track_id, f"objects.person_track_ids[{index}]")
    if len(track_ids) != len(set(track_ids)):
        _fail("objects.person_track_ids", "must contain unique track IDs")
    if int(count) != len(track_ids):
        _fail("objects.person_count", "must equal person_track_ids length")
    threshold = _number(evidence.get("threshold"), "evidence.threshold", 1)
    if not threshold.is_integer():
        _fail("evidence.threshold", "must be an integer")
    _number(evidence.get("above_threshold_duration_s"),
            "evidence.above_threshold_duration_s", 0)


def _validate_abandoned(objects: dict, evidence: dict) -> None:
    luggage = _dict(objects.get("luggage"), "objects.luggage")
    owner = _dict(objects.get("owner"), "objects.owner")
    _nonempty(luggage.get("physical_id"), "objects.luggage.physical_id")
    source_ids = luggage.get("source_track_ids")
    if not isinstance(source_ids, list) or not source_ids:
        _fail("objects.luggage.source_track_ids", "must be a non-empty list")
    for index, track_id in enumerate(source_ids):
        _track_id(track_id, f"objects.luggage.source_track_ids[{index}]")
    if len(source_ids) != len(set(source_ids)):
        _fail("objects.luggage.source_track_ids", "must contain unique track IDs")
    _bbox(luggage.get("bbox_xyxy"), "objects.luggage.bbox_xyxy")
    _track_id(owner.get("person_track_id"), "objects.owner.person_track_id")
    _number(evidence.get("stationary_duration_s"), "evidence.stationary_duration_s", 0)
    _number(evidence.get("owner_away_duration_s"), "evidence.owner_away_duration_s", 0)
    _number(evidence.get("owner_association_score"),
            "evidence.owner_association_score", 0, 1)
    if "luggage_quality_score" in evidence:
        _number(evidence["luggage_quality_score"], "evidence.luggage_quality_score", 0, 1)


def validate_event(event: Any) -> None:
    payload = event.to_dict() if hasattr(event, "to_dict") else event
    if not isinstance(payload, dict):
        _fail("event", "must be a CVEvent or object")
    missing, extra = FIELDS - payload.keys(), payload.keys() - FIELDS
    if missing:
        _fail("event", f"missing fields: {sorted(missing)}")
    if extra:
        _fail("event", f"unexpected fields: {sorted(extra)}")
    if payload["schema_version"] != SCHEMA_VERSION:
        _fail("schema_version", f"must equal {SCHEMA_VERSION}")
    _nonempty(payload["event_id"], "event_id")
    if payload["event_type"] not in EVENT_TYPES:
        _fail("event_type", f"must be one of {sorted(EVENT_TYPES)}")
    if payload["event_state"] not in EVENT_STATES:
        _fail("event_state", f"must be one of {sorted(EVENT_STATES)}")
    _nonempty(payload["camera_id"], "camera_id")
    timestamp = _nonempty(payload["event_time"], "event_time")
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as error:
        _fail("event_time", f"must be ISO-8601: {error}")
    if parsed.tzinfo is None:
        _fail("event_time", "must include a timezone offset")
    _number(payload["event_time_s"], "event_time_s", 0)
    _number(payload["cv_confidence"], "cv_confidence", 0, 1)
    objects = _dict(payload["objects"], "objects")
    evidence = _dict(payload["evidence"], "evidence")
    for field in ("spatial", "media", "diagnostics"):
        _dict(payload[field], field)
    validators = {
        "ZONE_INTRUSION": _validate_intrusion,
        "CROWD_THRESHOLD": _validate_crowd,
        "ABANDONED_OBJECT": _validate_abandoned,
    }
    validators[payload["event_type"]](objects, evidence)
