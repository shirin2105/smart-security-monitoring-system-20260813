"""Versioned placement-transition diagnostic sidecar projection."""

from __future__ import annotations

from typing import Any


PLACEMENT_DIAGNOSTIC_FIELDS = {
    "schema", "clip_id", "frame_id", "time_s", "physical_luggage_id",
    "person_track_id", "association_score", "candidate_eligible",
    "candidate_selected", "evidence_sufficient", "placement_predicate_passed",
    "sample_count", "interval_count", "duration_s", "bag_motion_norm",
    "aligned_moving_ratio", "median_direction_cosine",
    "relative_offset_spread_norm",
}


def placement_candidate_rows(
    *, clip_id: str, frame_id: int, time_s: float, physical_id: str,
    owner: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not owner:
        return []
    selected_id = owner.get("person_track_id")
    rows = []
    for candidate in owner.get("candidates", []):
        feature = candidate.get("placement_transition")
        if not feature:
            continue
        row = {
            "schema": "placement-transition-diagnostic-v1",
            "clip_id": clip_id,
            "frame_id": int(frame_id),
            "time_s": float(time_s),
            "physical_luggage_id": physical_id,
            "person_track_id": candidate["person_track_id"],
            "association_score": candidate.get("association_score"),
            "candidate_eligible": candidate.get("candidate_eligible"),
            "candidate_selected": selected_id == candidate["person_track_id"],
            **{key: feature.get(key) for key in PLACEMENT_DIAGNOSTIC_FIELDS
               if key != "schema" and key in feature},
        }
        rows.append(row)
    return rows
