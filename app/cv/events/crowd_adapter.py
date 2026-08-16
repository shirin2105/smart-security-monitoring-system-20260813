from __future__ import annotations

from typing import Any

from app.common.time_utils import calculate_duration_seconds
from app.cv.events.event_signal import EventSignal
from app.cv.events.frame_time import frame_time_seconds
from app.events.crowd import CrowdState, CrowdZoneStateTracker


class CrowdLifecycleAdapter:
    """Emits CROWD_THRESHOLD over the full camera frame (Product Policy v2).

    Zones/ROIs are no longer used for crowd counting; they remain reserved for
    ZONE_INTRUSION only. A single full-frame counter is kept per camera.
    """

    FULL_FRAME_ZONE_ID = "FULL_FRAME"

    def __init__(self, camera_id: str, zones_config: list[dict[str, Any]], rules_config: dict[str, Any]):
        self.camera_id = camera_id
        rules = rules_config.get("crowd", {})
        self.threshold = int(rules.get("count_threshold", 8))
        self.hold_seconds = float(rules.get("hold_seconds", 10.0))
        self.release_threshold = int(rules.get("release_threshold", 5))
        # Product Policy v2: one full-frame counter per camera (no per-zone ROI).
        self._tracker = CrowdZoneStateTracker(
            self.FULL_FRAME_ZONE_ID, self.threshold, self.hold_seconds, self.release_threshold
        )
        self._last_facts: dict[str, dict[str, Any]] = {}

    def evaluate(self, tracks: list[Any], frame_data: Any) -> list[EventSignal]:
        timestamp = frame_data.captured_at
        now_s = frame_time_seconds(frame_data)
        persons = [track for track in tracks if track.class_name == "person"]
        inside = {track.track_id: track for track in persons}
        count = len(inside)
        previous = self._tracker.current_state
        current = self._tracker.update(count, timestamp)
        signals = []
        if current == CrowdState.CROWD_ACTIVE:
            duration = calculate_duration_seconds(self._tracker.pending_started_at, timestamp)
            facts = {
                "track_ids": sorted(inside),
                "duration": max(0.0, duration),
                "confidence": min((t.confidence for t in inside.values()), default=0.0),
            }
            self._last_facts[self.FULL_FRAME_ZONE_ID] = facts
            signals.append(self._signal(True, timestamp, now_s, facts))
        elif previous == CrowdState.CROWD_ACTIVE and current == CrowdState.RECOVERING:
            signals.append(self._signal(False, timestamp, now_s, self._last_facts[self.FULL_FRAME_ZONE_ID]))
        return signals

    def _signal(self, active: bool, timestamp: str, now_s: float, facts: dict[str, Any]) -> EventSignal:
        return EventSignal(
            self.camera_id,
            "CROWD_THRESHOLD",
            self.FULL_FRAME_ZONE_ID,
            active,
            timestamp,
            now_s,
            float(facts["confidence"]),
            {"person_count": len(facts["track_ids"]), "person_track_ids": facts["track_ids"]},
            {"threshold": self.threshold, "above_threshold_duration_s": facts["duration"]},
            spatial={"zone_id": self.FULL_FRAME_ZONE_ID},
        )

    def reset(self) -> None:
        """Forget pending and active counts when source continuity has been lost."""
        self._tracker.current_state = CrowdState.NORMAL
        self._tracker.pending_started_at = None
        self._tracker.event_generated = False
        self._last_facts.clear()
