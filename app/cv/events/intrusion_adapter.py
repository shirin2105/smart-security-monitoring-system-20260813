from __future__ import annotations

from typing import Any

from app.common.enums import IntrusionState
from app.common.geometry import is_point_in_polygon, scale_polygon_to_frame
from app.common.time_utils import calculate_duration_seconds
from app.cv.events.event_signal import EventSignal
from app.events.temporal_state import TrackIntrusionStateTracker


def _media_seconds(frame_data: Any) -> float:
    fps = max(float(frame_data.source_fps), 1e-9)
    return max(0.0, float(frame_data.frame_id - 1) / fps)


class IntrusionLifecycleAdapter:
    """Preserves the existing dwell state machine and exposes lifecycle facts."""

    def __init__(self, camera_id: str, zones_config: list[dict[str, Any]],
                 rules_config: dict[str, Any]):
        self.camera_id = camera_id
        self.zones = [z for z in zones_config
                      if z.get("camera_id") == camera_id and z.get("enabled", True)]
        intrusion_cfg = rules_config.get("intrusion", {})
        self.dwell_seconds = float(intrusion_cfg.get("dwell_seconds", 1.0))
        self.exit_grace_seconds = float(intrusion_cfg.get("exit_grace_seconds", 0.5))
        self._states: dict[tuple[int, str], TrackIntrusionStateTracker] = {}
        self._active: set[tuple[int, str]] = set()
        self._last_facts: dict[tuple[int, str], tuple[Any, dict[str, Any]]] = {}

    def reload_zones(self, zones_config: list[dict[str, Any]]) -> None:
        new_zones = [z for z in zones_config
                     if z.get("camera_id") == self.camera_id and z.get("enabled", True)]
        if new_zones != self.zones:
            self.zones = new_zones

    def _get_scaled_polygon(self, polygon: list[list[float]], frame_data: Any) -> list[list[float]]:
        if getattr(frame_data, "image", None) is not None:
            h, w = frame_data.image.shape[:2]
            return scale_polygon_to_frame(polygon, frame_width=w, frame_height=h)
        return polygon

    def evaluate(self, tracks: list[Any], frame_data: Any) -> list[EventSignal]:
        timestamp, now_s = frame_data.captured_at, _media_seconds(frame_data)
        persons = {track.track_id: track for track in tracks if track.class_name == "person"}
        signals: list[EventSignal] = []
        observed: set[tuple[int, str]] = set()
        for track in persons.values():
            for zone in self.zones:
                key = (track.track_id, str(zone["zone_id"]))
                observed.add(key)
                state = self._states.setdefault(
                    key, TrackIntrusionStateTracker(track.track_id, self.dwell_seconds, self.exit_grace_seconds)
                )
                scaled_polygon = self._get_scaled_polygon(zone["polygon"], frame_data)
                if is_point_in_polygon(track.latest_foot_point, scaled_polygon):
                    lifecycle = state.update_inside(timestamp)
                    if lifecycle == IntrusionState.INTRUSION_ACTIVE:
                        duration = calculate_duration_seconds(state.entered_zone_at, timestamp)
                        facts = self._facts(track, zone["zone_id"], duration)
                        self._last_facts[key] = (track, facts)
                        self._active.add(key)
                        signals.append(self._signal(track, zone["zone_id"], True,
                                                    timestamp, now_s, facts))
                else:
                    was_active = key in self._active
                    lifecycle = state.update_outside(timestamp)
                    if lifecycle == IntrusionState.EXITED:
                        if was_active:
                            signals.append(self._end(key, timestamp, now_s))
                        self._reset(key)
                    elif lifecycle == IntrusionState.OUTSIDE:
                        self._reset(key)
        for key in list(self._active - observed):
            state = self._states.get(key)
            if state:
                lifecycle = state.update_outside(timestamp)
                if lifecycle == IntrusionState.EXITED:
                    signals.append(self._end(key, timestamp, now_s))
                    self._reset(key)
            else:
                signals.append(self._end(key, timestamp, now_s))
                self._reset(key)
        return signals

    @staticmethod
    def _facts(track: Any, zone_id: str, duration: float) -> dict[str, Any]:
        return {"persons": [{"track_id": track.track_id,
                              "bbox_xyxy": list(track.latest_bbox)}],
                "zone_id": str(zone_id), "inside_duration_s": max(0.0, duration)}

    def _signal(self, track: Any, zone_id: str, active: bool, timestamp: str,
                now_s: float, facts: dict[str, Any]) -> EventSignal:
        return EventSignal(
            self.camera_id, "ZONE_INTRUSION", f"{zone_id}:{track.track_id}", active,
            timestamp, now_s, float(track.confidence), {"persons": facts["persons"]},
            {"zone_id": facts["zone_id"], "inside_duration_s": facts["inside_duration_s"]},
            spatial={"zone_id": str(zone_id)},
        )

    def _end(self, key: tuple[int, str], timestamp: str, now_s: float) -> EventSignal:
        track, facts = self._last_facts[key]
        return self._signal(track, key[1], False, timestamp, now_s, facts)

    def _reset(self, key: tuple[int, str]) -> None:
        self._active.discard(key)
        self._states.pop(key, None)
