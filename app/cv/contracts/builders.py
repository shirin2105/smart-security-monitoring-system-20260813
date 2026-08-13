from __future__ import annotations

from copy import deepcopy
from typing import Any

from .cv_event import CVEvent
from .validation import SCHEMA_VERSION, validate_event


def _build(*, event_id: str, event_type: str, event_state: str, camera_id: str,
           event_time: str, event_time_s: float, cv_confidence: float,
           objects: dict[str, Any], evidence: dict[str, Any],
           spatial: dict[str, Any] | None, media: dict[str, Any] | None,
           diagnostics: dict[str, Any] | None) -> CVEvent:
    event = CVEvent(
        schema_version=SCHEMA_VERSION,
        event_id=event_id,
        event_type=event_type,
        event_state=event_state,
        camera_id=camera_id,
        event_time=event_time,
        event_time_s=event_time_s,
        cv_confidence=cv_confidence,
        objects=deepcopy(objects),
        evidence=deepcopy(evidence),
        spatial=deepcopy(spatial or {}),
        media=deepcopy(media or {}),
        diagnostics=deepcopy(diagnostics or {}),
    )
    validate_event(event)
    return event


def build_intrusion_event(*, event_id: str, event_state: str, camera_id: str,
                          event_time: str, event_time_s: float, cv_confidence: float,
                          persons: list[dict[str, Any]], zone_id: str,
                          inside_duration_s: float,
                          spatial: dict[str, Any] | None = None,
                          media: dict[str, Any] | None = None,
                          diagnostics: dict[str, Any] | None = None) -> CVEvent:
    return _build(
        event_id=event_id, event_type="ZONE_INTRUSION", event_state=event_state,
        camera_id=camera_id, event_time=event_time, event_time_s=event_time_s,
        cv_confidence=cv_confidence, objects={"persons": persons},
        evidence={"zone_id": zone_id, "inside_duration_s": inside_duration_s},
        spatial=spatial or {"zone_id": zone_id}, media=media, diagnostics=diagnostics,
    )


def build_crowd_event(*, event_id: str, event_state: str, camera_id: str,
                      event_time: str, event_time_s: float, cv_confidence: float,
                      person_track_ids: list[int], threshold: int,
                      above_threshold_duration_s: float,
                      spatial: dict[str, Any] | None = None,
                      media: dict[str, Any] | None = None,
                      diagnostics: dict[str, Any] | None = None) -> CVEvent:
    count = len(person_track_ids)
    return _build(
        event_id=event_id, event_type="CROWD_THRESHOLD", event_state=event_state,
        camera_id=camera_id, event_time=event_time, event_time_s=event_time_s,
        cv_confidence=cv_confidence,
        objects={"person_count": count, "person_track_ids": person_track_ids},
        evidence={"person_count": count, "threshold": threshold,
                  "above_threshold_duration_s": above_threshold_duration_s},
        spatial=spatial, media=media, diagnostics=diagnostics,
    )


def build_abandoned_event(*, event_id: str, event_state: str, camera_id: str,
                          event_time: str, event_time_s: float, cv_confidence: float,
                          physical_id: str, source_track_ids: list[int],
                          luggage_bbox_xyxy: list[float], owner_person_track_id: int,
                          stationary_duration_s: float, owner_away_duration_s: float,
                          owner_association_score: float,
                          luggage_quality_score: float | None = None,
                          spatial: dict[str, Any] | None = None,
                          media: dict[str, Any] | None = None,
                          diagnostics: dict[str, Any] | None = None) -> CVEvent:
    evidence = {
        "stationary_duration_s": stationary_duration_s,
        "owner_away_duration_s": owner_away_duration_s,
        "owner_association_score": owner_association_score,
    }
    if luggage_quality_score is not None:
        evidence["luggage_quality_score"] = luggage_quality_score
    return _build(
        event_id=event_id, event_type="ABANDONED_OBJECT", event_state=event_state,
        camera_id=camera_id, event_time=event_time, event_time_s=event_time_s,
        cv_confidence=cv_confidence,
        objects={
            "luggage": {"physical_id": physical_id,
                        "source_track_ids": source_track_ids,
                        "bbox_xyxy": luggage_bbox_xyxy},
            "owner": {"person_track_id": owner_person_track_id},
        },
        evidence=evidence, spatial=spatial, media=media, diagnostics=diagnostics,
    )
