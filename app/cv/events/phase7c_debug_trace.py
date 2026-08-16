"""Optional, behavior-neutral Phase 11B diagnostics for Phase7C."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.cv.events.phase7c_owner_association_trace import owner_candidate_rows
from app.cv.events.phase7c_placement_diagnostic_trace import placement_candidate_rows


class Phase7CDebugTrace:
    """Emit one deterministic diagnostic row for each luggage/frame observation."""

    def __init__(self, camera_id: str, config: dict[str, Any] | None = None) -> None:
        config = config or {}
        self.enabled = bool(config.get("enabled", False)) and bool(config.get("emit_trace_jsonl", False))
        self.camera_id = camera_id
        safe_camera_id = re.sub(r"[^A-Za-z0-9_.-]", "_", camera_id)
        self.path = Path(config.get("trace_output_dir", "artifacts/phase11b/traces")) / f"{safe_camera_id}.jsonl"
        self.owner_path = self.path.with_name(f"{safe_camera_id}-owner-association.jsonl")
        self.placement_path = self.path.with_name(f"{safe_camera_id}-placement-diagnostics-v1.jsonl")
        self._seen: set[tuple[str, int]] = set()
        self._physical_ids: list[tuple[set[int], str]] = []
        self._physical_counter = 0
        if self.enabled:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("", encoding="utf-8")
            self.owner_path.write_text("", encoding="utf-8")
            self.placement_path.write_text("", encoding="utf-8")

    def physical_id(self, track_id: int, result: dict[str, Any]) -> str:
        """Resolve trace identity without touching production adapter identity state."""
        source_ids = set(self._source_ids(result, track_id))
        for known_ids, physical_id in self._physical_ids:
            if known_ids & source_ids:
                known_ids.update(source_ids)
                return physical_id
        self._physical_counter += 1
        physical_id = f"LUG_{self._physical_counter:04d}"
        self._physical_ids.append((source_ids, physical_id))
        return physical_id

    def emit(
        self,
        *,
        frame_id: int,
        time_s: float,
        physical_id: str,
        track: Any,
        result: dict[str, Any],
        event_emitted: bool,
    ) -> None:
        if not self.enabled or (physical_id, frame_id) in self._seen:
            return
        self._seen.add((physical_id, frame_id))
        source_ids = self._source_ids(result, int(track.track_id))
        quality = self._quality(result, int(track.track_id))
        physical = self._physical(result, source_ids)
        stationary = self._stationary(physical)
        owner_precheck = self._owner_precheck(result, physical)
        owner = self._owner(result, physical)
        event = self._event(result, source_ids)
        state, failure_hint = self._state(quality, physical, stationary, owner, event)
        bbox = [float(value) for value in track.latest_bbox]
        owner_away = None
        if owner and owner.get("owner_last_near_s") is not None:
            owner_away = max(0.0, time_s - float(owner["owner_last_near_s"]))
        owner_candidates = owner.get("candidates", []) if owner else []
        row = {
            "clip_id": self.camera_id,
            "camera_id": self.camera_id,
            "frame_id": int(frame_id),
            "time_s": float(time_s),
            "physical_luggage_id": physical_id,
            "source_track_ids": source_ids,
            "bbox": bbox,
            "det_confidence": float(track.confidence),
            "quality_score": quality.get("rolling_good_ratio") if quality else None,
            "quality_pass": quality.get("passed") if quality else None,
            "stationary_state": state if state.startswith("STATIONARY") else None,
            "stationary_duration_s": stationary.get("duration_s") if stationary else None,
            "owner_track_id": owner.get("person_track_id") if owner else None,
            "owner_association_score": owner.get("association_score") if owner else None,
            "owner_distance": None,
            "owner_near": None,
            "owner_away_duration_s": owner_away,
            "luggage_bbox": bbox,
            "stationary_since_s": stationary.get("start_s") if stationary else None,
            "stationary_confirmed_at_s": stationary.get("confirmed_at_s") if stationary else None,
            "owner_candidate_person_ids": [item["person_track_id"] for item in owner_candidates],
            "owner_candidate_bboxes": [item.get("candidate_bboxes", []) for item in owner_candidates],
            "owner_candidate_min_distances": [item.get("min_distance_norm") for item in owner_candidates],
            "owner_candidate_scores": [item.get("association_score") for item in owner_candidates],
            "owner_candidate_inside_ratios": [item.get("inside_ratio") for item in owner_candidates],
            "owner_candidate_near_ratios": [item.get("near_ratio") for item in owner_candidates],
            "owner_candidate_proximity_ratios": [item.get("proximity_ratio") for item in owner_candidates],
            "owner_candidate_overlap_seconds": [item.get("overlap_s") for item in owner_candidates],
            "owner_candidate_temporal_overlap_ratios": [item.get("temporal_overlap_ratio") for item in owner_candidates],
            "owner_candidate_score_components": [{
                "inside": item.get("inside_score_component"),
                "proximity": item.get("proximity_score_component"),
                "near": item.get("near_score_component"),
                "overlap": item.get("overlap_score_component"),
            } for item in owner_candidates],
            "owner_candidate_min_association_scores": [item.get("min_association_score") for item in owner_candidates],
            "owner_candidate_eligible": [item.get("candidate_eligible") for item in owner_candidates],
            "owner_candidate_selected": [item.get("candidate_selected") for item in owner_candidates],
            "owner_candidate_confidences": [item.get("person_confidence") for item in owner_candidates],
            "owner_candidate_min_distances_px": [item.get("min_distance_px") for item in owner_candidates],
            "owner_candidate_present_before_stationary": [item.get("candidate_present_before_stationary") for item in owner_candidates],
            "owner_candidate_present_at_stationary": [item.get("candidate_present_at_stationary") for item in owner_candidates],
            "owner_candidate_present_after_stationary": [item.get("candidate_present_after_stationary") for item in owner_candidates],
            "owner_candidate_track_fragmented": [item.get("person_track_fragmented") for item in owner_candidates],
            "owner_candidate_first_seen_s": [item.get("first_seen_s") for item in owner_candidates],
            "owner_candidate_last_seen_s": [item.get("last_seen_s") for item in owner_candidates],
            "owner_candidate_track_ages_s": [item.get("track_age_s") for item in owner_candidates],
            "selected_owner_person_id": owner.get("person_track_id") if owner else None,
            "owner_selection_reason": owner.get("selection_reason") if owner else None,
            "owner_rejection_reason": owner.get("rejection_reason") if owner else None,
            "owner_history_window_start_s": owner.get("history_window_start_s") if owner else None,
            "owner_history_window_end_s": owner.get("history_window_end_s") if owner else None,
            "owner_eventually_associated": bool(owner and owner.get("person_track_id") is not None),
            "owner_association_precheck_eligible": owner_precheck.get("eligible") if owner_precheck else None,
            "owner_association_precheck_rejection_reason": owner_precheck.get("rejection_reason") if owner_precheck else None,
            "candidate_state": state,
            "event_emitted": bool(event_emitted),
            "failure_hint": failure_hint,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
        candidate_rows = owner_candidate_rows(
            clip_id=self.camera_id, frame_id=frame_id, time_s=time_s,
            physical_id=physical_id, luggage_bbox=bbox, stationary=stationary, owner=owner,
        )
        if candidate_rows:
            with self.owner_path.open("a", encoding="utf-8") as handle:
                for candidate_row in candidate_rows:
                    handle.write(json.dumps(candidate_row, sort_keys=True, separators=(",", ":")) + "\n")
        placement_rows = placement_candidate_rows(
            clip_id=self.camera_id, frame_id=frame_id, time_s=time_s,
            physical_id=physical_id, owner=owner,
        )
        if placement_rows:
            with self.placement_path.open("a", encoding="utf-8") as handle:
                for placement_row in placement_rows:
                    handle.write(json.dumps(placement_row, allow_nan=False, sort_keys=True,
                                            separators=(",", ":")) + "\n")

    @staticmethod
    def _source_ids(result: dict[str, Any], track_id: int) -> list[int]:
        for item in result.get("physical_luggage", []):
            ids = [int(value) for value in item["source_track_ids"]]
            if track_id in ids:
                return ids
        return [track_id]

    @staticmethod
    def _quality(result: dict[str, Any], track_id: int) -> dict[str, Any] | None:
        return result.get("quality_report", {}).get(str(track_id))

    @staticmethod
    def _physical(result: dict[str, Any], source_ids: list[int]) -> dict[str, Any] | None:
        wanted = set(source_ids)
        return next((item for item in result.get("physical_luggage", []) if wanted & set(item["source_track_ids"])), None)

    @staticmethod
    def _stationary(physical: dict[str, Any] | None) -> dict[str, Any] | None:
        if not physical:
            return None
        runs = physical.get("stationary_runs", [])
        return runs[-1] if runs else None

    @staticmethod
    def _owner(result: dict[str, Any], physical: dict[str, Any] | None) -> dict[str, Any] | None:
        if not physical:
            return None
        physical_id = physical["physical_id"]
        reports = [item for item in result.get("owner_associations", []) if item["physical_id"] == physical_id]
        return max(reports, key=lambda item: float(item["association_score"]), default=None)

    @staticmethod
    def _owner_precheck(result: dict[str, Any], physical: dict[str, Any] | None) -> dict[str, Any] | None:
        if not physical:
            return None
        reports = [
            item for item in result.get("owner_prechecks", [])
            if item["physical_id"] == physical["physical_id"]
        ]
        return max(reports, key=lambda item: float(item["stationary_confirmed_s"]), default=None)

    @staticmethod
    def _event(result: dict[str, Any], source_ids: list[int]) -> dict[str, Any] | None:
        wanted = set(source_ids)
        return next((item for item in result.get("events", []) if wanted & set(item["source_track_ids"])), None)

    @staticmethod
    def _state(quality, physical, stationary, owner, event) -> tuple[str, str | None]:
        if not quality or not quality.get("passed"):
            return "QUALITY_REJECTED", "QUALITY_REJECT"
        if not physical:
            return "TRACKED", "STITCH_FAILURE"
        if not stationary:
            return "STATIONARY_PENDING", "STATIONARY_NOT_CONFIRMED"
        if not owner or owner.get("person_track_id") is None:
            return "OWNER_UNASSIGNED", "OWNER_NOT_ASSOCIATED"
        if event:
            return "CANDIDATE", None
        return "OWNER_AWAY_PENDING", "OWNER_AWAY_NOT_REACHED"
