from __future__ import annotations

from typing import Any

from app.common.time_utils import calculate_duration_seconds
from app.cv.events.event_signal import EventSignal
from app.events.crowd import CrowdState, CrowdZoneStateTracker


def _media_seconds(frame_data: Any) -> float:
    fps = max(float(frame_data.source_fps), 1e-9)
    return max(0.0, float(frame_data.frame_id - 1) / fps)


class CrowdLifecycleAdapter:
    """Uses the production crowd hold/release tracker and emits zone facts."""

    def __init__(self, camera_id: str, zones_config: list[dict[str, Any]],
                 rules_config: dict[str, Any]):
        self.camera_id = camera_id
        self.zones = [z for z in zones_config
                      if z.get("camera_id") == camera_id and z.get("enabled", True)]
        rules = rules_config.get("crowd", {})
        self.threshold = int(rules.get("count_threshold", 8))
        self.hold_seconds = float(rules.get("hold_seconds", 10.0))
        self.release_threshold = int(rules.get("release_threshold", 5))
        self._states: dict[str, CrowdZoneStateTracker] = {}
        self._last_facts: dict[str, dict[str, Any]] = {}

    def evaluate(self, tracks: list[Any], frame_data: Any) -> list[EventSignal]:
        from app.common.geometry import is_point_in_polygon

        timestamp = frame_data.captured_at
        now_s = _media_seconds(frame_data)
        persons = [track for track in tracks if track.class_name == "person"]
        signals = []
        for zone in self.zones:
            zone_id = str(zone["zone_id"])
            inside = {track.track_id: track for track in persons
                      if is_point_in_polygon(track.latest_foot_point, zone["polygon"])}
            tracker = self._states.setdefault(zone_id, CrowdZoneStateTracker(
                zone_id, self.threshold, self.hold_seconds, self.release_threshold
            ))
            previous = tracker.current_state
            current = tracker.update(len(inside), timestamp)
            if current == CrowdState.CROWD_ACTIVE:
                duration = calculate_duration_seconds(tracker.pending_started_at, timestamp)
                facts = {"track_ids": sorted(inside), "duration": max(0.0, duration),
                         "confidence": min((t.confidence for t in inside.values()), default=0.0)}
                self._last_facts[zone_id] = facts
                signals.append(self._signal(zone_id, True, timestamp, now_s, facts))
            elif previous == CrowdState.CROWD_ACTIVE and current == CrowdState.RECOVERING:
                signals.append(self._signal(zone_id, False, timestamp, now_s,
                                            self._last_facts[zone_id]))
        return signals

    def _signal(self, zone_id: str, active: bool, timestamp: str, now_s: float,
                facts: dict[str, Any]) -> EventSignal:
        return EventSignal(
            self.camera_id, "CROWD_THRESHOLD", zone_id, active, timestamp, now_s,
            float(facts["confidence"]),
            {"person_count": len(facts["track_ids"]),
             "person_track_ids": facts["track_ids"]},
            {"threshold": self.threshold,
             "above_threshold_duration_s": facts["duration"]},
            spatial={"zone_id": zone_id},
        )
