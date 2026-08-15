"""Phase 11A hardened GT validation.

Checks that a ground-truth file is internally consistent and safe to benchmark:
valid event types, clips present in the manifest, ordered timing
(start <= trigger <= end), trigger within clip duration, unique event IDs,
consistent camera_id, required zone present, and only REVIEWED clips are
included (EXCLUDED clips skipped).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from app.evaluation.phase11_schema import VALID_EVENT_TYPES, GroundTruthEvent

REVIEW_STATUSES = {"UNREVIEWED", "REVIEWED", "NEEDS_SECOND_REVIEW", "EXCLUDED"}


class GTIssue:
    def __init__(self, clip_id: str, event_id: str | None, severity: str, message: str) -> None:
        self.clip_id = clip_id
        self.event_id = event_id
        self.severity = severity  # error | warning
        self.message = message

    def to_dict(self) -> dict[str, Any]:
        return {"clip_id": self.clip_id, "event_id": self.event_id, "severity": self.severity,
                "message": self.message}

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"GTIssue({self.severity}, {self.clip_id}, {self.message})"


class GroundTruthValidator:
    def __init__(
        self,
        manifest: dict[str, Any],
        review_status: dict[str, dict[str, Any]] | None = None,
        clip_durations: dict[str, float] | None = None,
        zone_by_clip: dict[str, list[str]] | None = None,
    ) -> None:
        self.manifest = manifest
        self.clips = {clip["clip_id"]: clip for clip in manifest.get("clips", [])}
        self.review_status = review_status or {}
        self.clip_durations = clip_durations or {}
        self.zone_by_clip = zone_by_clip or {}

    def validate(self, gt_events: Iterable[GroundTruthEvent]) -> tuple[list[GroundTruthEvent], list[GTIssue]]:
        """Validate GT; returns (usable_events, issues)."""
        issues: list[GTIssue] = []
        usable: list[GroundTruthEvent] = []
        seen_ids: set[tuple[str, str]] = set()

        for event in gt_events:
            clip_id = event.clip_id
            key = (clip_id, event.event_id)

            if key in seen_ids:
                issues.append(GTIssue(clip_id, event.event_id, "error", "duplicate event_id"))
                continue
            seen_ids.add(key)

            if event.event_type not in VALID_EVENT_TYPES:
                issues.append(GTIssue(clip_id, event.event_id, "error",
                                      f"invalid event_type {event.event_type!r}"))
                continue
            if clip_id not in self.clips:
                issues.append(GTIssue(clip_id, event.event_id, "error", "clip not in manifest"))
                continue
            cam = self.clips[clip_id]["camera_id"]
            if event.camera_id != cam:
                issues.append(GTIssue(clip_id, event.event_id, "error",
                                      f"camera_id mismatch {event.camera_id!r} != {cam!r}"))
                continue
            if not (event.start_s <= event.trigger_time_s <= event.end_s):
                issues.append(GTIssue(clip_id, event.event_id, "error",
                                      f"timing order violated: {event.start_s} <= {event.trigger_time_s} <= {event.end_s}"))
                continue
            duration = self.clip_durations.get(clip_id)
            if duration is not None and event.end_s > duration + 1.0:
                issues.append(GTIssue(clip_id, event.event_id, "error",
                                      f"end_s {event.end_s} exceeds clip duration {duration}"))
                continue
            if event.zone_id:
                zones = self.zone_by_clip.get(clip_id, [])
                if event.zone_id not in zones:
                    issues.append(GTIssue(clip_id, event.event_id, "error",
                                          f"zone {event.zone_id!r} not defined for clip {clip_id}"))

            status = self.review_status.get(clip_id, {}).get("review_status", "UNREVIEWED")
            if status == "EXCLUDED":
                issues.append(GTIssue(clip_id, event.event_id, "warning",
                                      f"clip {clip_id} is EXCLUDED; event skipped from benchmark"))
                continue
            if status == "UNREVIEWED":
                issues.append(GTIssue(clip_id, event.event_id, "warning",
                                      f"clip {clip_id} is UNREVIEWED; hardened benchmark requires REVIEWED"))
            usable.append(event)

        return usable, issues


def _to_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def load_review_status(path: str | Path) -> dict[str, dict[str, Any]]:
    """Load clip_review_status.csv into {clip_id: row}."""
    import csv

    statuses: dict[str, dict[str, Any]] = {}
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            clip_id = str(row.get("clip_id", "")).strip()
            if not clip_id:
                continue
            statuses[clip_id] = {
                "review_status": row.get("review_status", "UNREVIEWED"),
                "positive_negative": row.get("positive_negative", ""),
                "gt_event_count": int(row.get("gt_event_count") or 0),
                "roi_verified": _to_bool(row.get("roi_verified")),
                "timing_verified": _to_bool(row.get("timing_verified")),
                "hard_case": _to_bool(row.get("hard_case")),
                "notes": row.get("notes", ""),
            }
    return statuses


def validate_review_statuses(statuses: dict[str, dict[str, Any]]) -> list[GTIssue]:
    issues: list[GTIssue] = []
    for clip_id, row in statuses.items():
        status = row.get("review_status")
        if status not in REVIEW_STATUSES:
            issues.append(GTIssue(clip_id, None, "error", f"invalid review_status {status!r}"))
    return issues
