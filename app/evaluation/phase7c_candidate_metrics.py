from __future__ import annotations

from statistics import mean, median
from typing import Any

from app.cv.phase7c_tracking.event_contract import AbandonedObjectCandidate


def _p90(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, -(-9 * len(ordered) // 10) - 1)]


def evaluate_phase7c_candidates(
    events: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    """Score HITL candidates without representing them as confirmed alerts."""
    processed_seconds = float(manifest["processed_seconds"])
    if processed_seconds <= 0:
        raise ValueError("processed_seconds must be positive")

    tolerance = manifest.get("tolerance", {})
    early = float(tolerance.get("early_s", 0.0))
    late = float(tolerance.get("late_s", 0.0))
    labels = sorted(
        manifest.get("labels", []),
        key=lambda item: (
            float(item.get("end_s", item["start_s"])) + late,
            float(item["start_s"]),
            str(item["label_id"]),
        ),
    )
    candidates = [AbandonedObjectCandidate.from_mapping(event) for event in events]
    remaining = {candidate.event_id: candidate for candidate in candidates}
    matches: list[dict[str, Any]] = []
    false_negative_ids: list[str] = []

    for label in labels:
        start = float(label["start_s"])
        end = float(label.get("end_s", start))
        eligible = [
            candidate
            for candidate in remaining.values()
            if start - early <= candidate.candidate_time_s <= end + late
        ]
        if not eligible:
            false_negative_ids.append(str(label["label_id"]))
            continue
        candidate = min(
            eligible,
            key=lambda item: (item.candidate_time_s, item.event_id),
        )
        remaining.pop(candidate.event_id)
        matches.append({
            "label_id": str(label["label_id"]),
            "event_id": candidate.event_id,
            "delay_seconds": candidate.candidate_time_s - start,
        })

    tp = len(matches)
    fp = len(remaining)
    fn = len(false_negative_ids)
    precision_denominator = tp + fp
    recall_denominator = tp + fn
    delays = [float(item["delay_seconds"]) for item in matches]
    processed_hours = processed_seconds / 3600.0

    return {
        "evaluation_scope": "ABANDONED_OBJECT_CANDIDATE_ONLY",
        "confirmed_alarm_metrics": False,
        "overall": {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "label_count": tp + fn,
            "emitted_candidate_count": tp + fp,
            "precision": None if not precision_denominator else tp / precision_denominator,
            "recall": None if not recall_denominator else tp / recall_denominator,
            "processed_video_hours": processed_hours,
            "false_candidates_per_video_hour": fp / processed_hours,
            "false_alarms_per_video_hour": None,
            "matched_delay": {
                "count": len(delays),
                "mean_seconds": mean(delays) if delays else None,
                "median_seconds": median(delays) if delays else None,
                "p90_seconds": _p90(delays),
            },
        },
        "matches": matches,
        "false_positive_event_ids": sorted(remaining),
        "false_negative_label_ids": false_negative_ids,
        "scope_note": (
            "False-candidate rate is reported for HITL/backend candidates. "
            "False-alarm rate is undefined because Phase 7C emits no confirmed alarms."
        ),
    }
