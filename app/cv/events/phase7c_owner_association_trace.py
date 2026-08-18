"""Candidate-level owner association trace rows for diagnostic runs."""

from __future__ import annotations

from typing import Any

OWNER_ASSOC_FIELDS = {
    "clip_id", "frame_id", "time_s", "physical_luggage_id", "luggage_bbox",
    "stationary_since_s", "stationary_confirmed_at_s", "person_track_id", "person_bbox",
    "person_confidence", "person_track_age_s", "distance_px", "distance_norm", "overlap_s",
    "temporal_overlap_ratio", "association_score", "min_association_score", "candidate_eligible",
    "candidate_selected", "rejection_reason", "candidate_first_seen_s", "candidate_last_seen_s",
    "candidate_present_before_stationary", "candidate_present_at_stationary",
    "candidate_present_after_stationary", "person_track_fragmented",
}


def owner_candidate_rows(
    *, clip_id: str, frame_id: int, time_s: float, physical_id: str,
    luggage_bbox: list[float], stationary: dict[str, Any] | None,
    owner: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Return one accepted-schema row per actual owner candidate."""
    if not owner:
        return []
    rows = []
    selected_id = owner.get("person_track_id")
    for candidate in owner.get("candidates", []):
        selected = selected_id is not None and candidate["person_track_id"] == selected_id
        if selected:
            rejection = None
        elif not candidate.get("candidate_eligible"):
            rejection = "CANDIDATE_INELIGIBLE"
        else:
            rejection = owner.get("rejection_reason") or "LOWER_ASSOCIATION_SCORE"
        boxes = candidate.get("candidate_bboxes", [])
        rows.append({
            "clip_id": clip_id, "frame_id": int(frame_id), "time_s": float(time_s),
            "physical_luggage_id": physical_id, "luggage_bbox": luggage_bbox,
            "stationary_since_s": stationary.get("start_s") if stationary else None,
            "stationary_confirmed_at_s": stationary.get("confirmed_at_s") if stationary else None,
            "person_track_id": candidate["person_track_id"],
            "person_bbox": boxes[-1] if boxes else None,
            "person_confidence": candidate.get("person_confidence"),
            "person_track_age_s": candidate.get("track_age_s"),
            "distance_px": candidate.get("min_distance_px"),
            "distance_norm": candidate.get("min_distance_norm"),
            "overlap_s": candidate.get("overlap_s"),
            "temporal_overlap_ratio": candidate.get("temporal_overlap_ratio"),
            "association_score": candidate.get("association_score"),
            "min_association_score": candidate.get("min_association_score"),
            "candidate_eligible": candidate.get("candidate_eligible"),
            "candidate_selected": selected, "rejection_reason": rejection,
            "candidate_first_seen_s": candidate.get("first_seen_s"),
            "candidate_last_seen_s": candidate.get("last_seen_s"),
            "candidate_present_before_stationary": candidate.get("candidate_present_before_stationary"),
            "candidate_present_at_stationary": candidate.get("candidate_present_at_stationary"),
            "candidate_present_after_stationary": candidate.get("candidate_present_after_stationary"),
            "person_track_fragmented": candidate.get("person_track_fragmented"),
        })
    return rows
