from __future__ import annotations

from typing import Any

from app.common.enums import IntrusionState
from app.common.geometry import is_point_in_polygon
from app.common.time_utils import calculate_duration_seconds
from app.cv.events.event_signal import EventSignal
from app.cv.events.frame_time import frame_time_seconds
from app.events.temporal_state import TrackIntrusionStateTracker


class IntrusionLifecycleAdapter:
    """Preserves the existing dwell state machine and exposes lifecycle facts."""

    def __init__(self, camera_id: str, zones_config: list[dict[str, Any]], rules_config: dict[str, Any]):
        self.camera_id = camera_id
        self.zones = [z for z in zones_config if z.get("camera_id") == camera_id and z.get("enabled", True)]
        self.dwell_seconds = float(rules_config.get("intrusion", {}).get("dwell_seconds", 2.0))
        self._states: dict[tuple[int, str], TrackIntrusionStateTracker] = {}
        self._active: set[tuple[int, str]] = set()
        self._last_facts: dict[tuple[int, str], tuple[Any, dict[str, Any]]] = {}

    def evaluate(self, tracks: list[Any], frame_data: Any) -> list[EventSignal]:
        timestamp, now_s = frame_data.captured_at, frame_time_seconds(frame_data)
        persons = {track.track_id: track for track in tracks if track.class_name == "person"}
        signals: list[EventSignal] = []
        observed: set[tuple[int, str]] = set()
        for track in persons.values():
            for zone in self.zones:
                key = (track.track_id, str(zone["zone_id"]))
                observed.add(key)
                state = self._states.setdefault(key, TrackIntrusionStateTracker(track.track_id, self.dwell_seconds))
                if is_point_in_polygon(track.latest_foot_point, zone["polygon"]):
                    lifecycle = state.update_inside(timestamp)
                    if lifecycle == IntrusionState.INTRUSION_ACTIVE:
                        duration = calculate_duration_seconds(state.entered_zone_at, timestamp)
                        facts = self._facts(track, zone["zone_id"], duration)
                        self._last_facts[key] = (track, facts)
                        self._active.add(key)
                        signals.append(self._signal(track, zone["zone_id"], True, timestamp, now_s, facts))
                else:
                    was_active = key in self._active
                    state.update_outside()
                    if was_active:
                        signals.append(self._end(key, timestamp, now_s))
                    self._reset(key)
        for key in self._active - observed:
            signals.append(self._end(key, timestamp, now_s))
            self._reset(key)
        return signals

    @staticmethod
    def _facts(track: Any, zone_id: str, duration: float) -> dict[str, Any]:
        return {
            "persons": [{"track_id": track.track_id, "bbox_xyxy": list(track.latest_bbox)}],
            "zone_id": str(zone_id),
            "inside_duration_s": max(0.0, duration),
        }

    def _signal(
        self, track: Any, zone_id: str, active: bool, timestamp: str, now_s: float, facts: dict[str, Any]
    ) -> EventSignal:
        return EventSignal(
            self.camera_id,
            "ZONE_INTRUSION",
            f"{zone_id}:{track.track_id}",
            active,
            timestamp,
            now_s,
            float(track.confidence),
            {"persons": facts["persons"]},
            {"zone_id": facts["zone_id"], "inside_duration_s": facts["inside_duration_s"]},
            spatial={"zone_id": str(zone_id)},
        )

    def _end(self, key: tuple[int, str], timestamp: str, now_s: float) -> EventSignal:
        track, facts = self._last_facts[key]
        return self._signal(track, key[1], False, timestamp, now_s, facts)

    def _reset(self, key: tuple[int, str]) -> None:
        self._active.discard(key)
        self._states.pop(key, None)

    def reset(self) -> None:
        """Forget dwell state when source continuity has been lost."""
        self._states.clear()
        self._active.clear()
        self._last_facts.clear()
