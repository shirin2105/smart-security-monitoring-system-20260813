from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

from app.cv.contracts.builders import (
    build_abandoned_event,
    build_crowd_event,
    build_intrusion_event,
)
from app.cv.contracts.cv_event import CVEvent
from app.cv.events.event_signal import EventSignal


@dataclass(slots=True)
class _ActiveEvent:
    event_id: str
    last_emitted_s: float
    fingerprint: str
    signal: EventSignal


class CVEventManager:
    """Per-worker lifecycle registry with stable IDs and output deduplication."""

    def __init__(self, camera_id: str, update_interval_s: float = 1.0,
                 run_id: str | None = None):
        if not camera_id:
            raise ValueError("camera_id must be non-empty")
        if update_interval_s < 0:
            raise ValueError("update_interval_s must be non-negative")
        self.camera_id = camera_id
        self.update_interval_s = float(update_interval_s)
        self.run_id = run_id or uuid.uuid4().hex
        self._active: dict[tuple[str, str, str], _ActiveEvent] = {}
        self._last_seen_s: dict[tuple[str, str, str], float] = {}
        self._counter = 0

    def process(self, signal: EventSignal) -> CVEvent | None:
        if signal.camera_id != self.camera_id:
            raise ValueError("signal camera_id does not match manager camera_id")
        previous_time = self._last_seen_s.get(signal.key)
        if previous_time is not None and signal.event_time_s < previous_time:
            raise ValueError("event signal time cannot move backwards")
        self._last_seen_s[signal.key] = signal.event_time_s

        active = self._active.get(signal.key)
        fingerprint = self._fingerprint(signal)
        if signal.active and active is None:
            self._counter += 1
            event_id = f"{self.camera_id}-{signal.event_type}-{self.run_id}-{self._counter:06d}"
            event = self._build(signal, event_id, "START")
            self._active[signal.key] = _ActiveEvent(
                event_id, signal.event_time_s, fingerprint, signal
            )
            return event
        if signal.active:
            assert active is not None
            active.signal = signal
            if fingerprint == active.fingerprint:
                return None
            if signal.event_time_s - active.last_emitted_s < self.update_interval_s:
                return None
            event = self._build(signal, active.event_id, "UPDATE")
            active.last_emitted_s = signal.event_time_s
            active.fingerprint = fingerprint
            return event
        if active is None:
            return None

        end_signal = signal if signal.objects and signal.evidence else active.signal
        event = self._build(end_signal, active.event_id, "END", signal)
        del self._active[signal.key]
        return event

    def process_all(self, signals: list[EventSignal]) -> list[CVEvent]:
        return [event for signal in signals if (event := self.process(signal)) is not None]

    def end_all(self) -> list[CVEvent]:
        """Close every active lifecycle at its last observed media timestamp."""
        events = [
            self._build(active.signal, active.event_id, "END")
            for active in self._active.values()
        ]
        self._active.clear()
        return events

    def discard(self, event_id: str) -> None:
        """Forget a lifecycle whose START could not cross the publisher boundary."""
        self._active = {
            key: active for key, active in self._active.items()
            if active.event_id != event_id
        }

    @staticmethod
    def _fingerprint(signal: EventSignal) -> str:
        return json.dumps(
            [signal.objects, signal.evidence, signal.spatial, signal.media],
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _build(signal: EventSignal, event_id: str, state: str,
               timing: EventSignal | None = None) -> CVEvent:
        clock = timing or signal
        common = dict(
            event_id=event_id,
            event_state=state,
            camera_id=signal.camera_id,
            event_time=clock.event_time,
            event_time_s=clock.event_time_s,
            cv_confidence=signal.cv_confidence,
            spatial=signal.spatial,
            media=signal.media,
            diagnostics=signal.diagnostics,
        )
        if signal.event_type == "ZONE_INTRUSION":
            return build_intrusion_event(
                **common,
                persons=signal.objects["persons"],
                zone_id=signal.evidence["zone_id"],
                inside_duration_s=signal.evidence["inside_duration_s"],
            )
        if signal.event_type == "CROWD_THRESHOLD":
            return build_crowd_event(
                **common,
                person_track_ids=signal.objects["person_track_ids"],
                threshold=signal.evidence["threshold"],
                above_threshold_duration_s=signal.evidence["above_threshold_duration_s"],
            )
        return build_abandoned_event(
            **common,
            physical_id=signal.objects["luggage"]["physical_id"],
            source_track_ids=signal.objects["luggage"]["source_track_ids"],
            luggage_bbox_xyxy=signal.objects["luggage"]["bbox_xyxy"],
            owner_person_track_id=signal.objects["owner"]["person_track_id"],
            stationary_duration_s=signal.evidence["stationary_duration_s"],
            owner_away_duration_s=signal.evidence["owner_away_duration_s"],
            owner_association_score=signal.evidence["owner_association_score"],
            luggage_quality_score=signal.evidence.get("luggage_quality_score"),
        )
