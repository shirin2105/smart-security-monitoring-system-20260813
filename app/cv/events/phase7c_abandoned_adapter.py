from __future__ import annotations

from typing import Any

from app.cv.events.event_signal import EventSignal
from app.cv.events.frame_time import frame_time_seconds
from kaggle_pipeline.phase7c_kernel.phase7c_core import (
    OwnerConfig,
    Phase7CConfig,
    QualityConfig,
    StationaryConfig,
    StitchConfig,
    bbox_diag,
    infer_phase7c,
    point_to_bbox_distance,
)


class Phase7CAbandonedAdapter:
    """Thin streaming adapter over the unchanged, production Phase7C reasoning core."""

    def __init__(self, camera_id: str, config: dict[str, Any] | None = None, fps_hint: float = 5.0):
        self.camera_id = camera_id
        cfg = config or {}
        self.config = Phase7CConfig(
            quality=QualityConfig(**cfg.get("quality", {})),
            stitch=StitchConfig(**cfg.get("stitch", {})),
            stationary=StationaryConfig(**cfg.get("stationary", {})),
            owner=OwnerConfig(**cfg.get("owner", {})),
            roi_polygon=cfg.get("valid_floor_roi_polygon"),
        )
        self.fps_hint = float(fps_hint)
        self._rows: list[dict[str, Any]] = []
        self._active: set[str] = set()
        self._retired: set[str] = set()
        self._last_signals: dict[str, EventSignal] = {}
        self._physical_ids: list[tuple[set[int], str]] = []
        self._physical_counter = 0
        longest_rule_s = max(
            self.config.quality.window_s,
            self.config.stationary.window_s + self.config.stationary.hold_s,
            self.config.owner.away_hold_s,
        )
        self._history_seconds = max(30.0, longest_rule_s * 4.0)

    def evaluate(self, tracks: list[Any], frame_data: Any) -> list[EventSignal]:
        now_s = frame_time_seconds(frame_data)
        current = {track.track_id: track for track in tracks}
        for track in tracks:
            box = [float(value) for value in track.latest_bbox]
            self._rows.append(
                {
                    "frame_index": int(frame_data.frame_id),
                    "timestamp_s": now_s,
                    "global_track_id": int(track.track_id),
                    "class_name": track.class_name,
                    "bbox_xyxy": box,
                    "center_xy": [(box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0],
                    "confidence": float(track.confidence),
                }
            )
        cutoff_s = now_s - self._history_seconds
        if cutoff_s > 0:
            self._rows = [row for row in self._rows if row["timestamp_s"] >= cutoff_s]
        result = infer_phase7c(self._rows, self.config, fps_hint=self.fps_hint)
        signals: list[EventSignal] = []
        seen: set[str] = set()
        quality = result["quality_report"]
        for event in result["events"]:
            source_ids = {int(value) for value in event["source_track_ids"]}
            physical_id = self._stable_physical_id(source_ids)
            if physical_id in self._retired:
                continue
            seen.add(physical_id)
            bag = next(
                (
                    current.get(int(track_id))
                    for track_id in reversed(event["source_track_ids"])
                    if int(track_id) in current
                ),
                None,
            )
            owner = current.get(int(event["owner_person_track_id"]))
            owner_near = False
            if bag is not None and owner is not None:
                owner_near = (
                    point_to_bbox_distance(
                        [
                            (bag.latest_bbox[0] + bag.latest_bbox[2]) / 2.0,
                            (bag.latest_bbox[1] + bag.latest_bbox[3]) / 2.0,
                        ],
                        owner.latest_bbox,
                    )
                    / bbox_diag(owner.latest_bbox)
                    <= self.config.owner.near_norm
                )
            if bag is None or owner_near:
                if physical_id in self._active:
                    signals.append(self._end(physical_id, frame_data.captured_at, now_s))
                    self._active.remove(physical_id)
                    self._retired.add(physical_id)
                continue
            profiles = [quality.get(str(track_id)) for track_id in event["source_track_ids"]]
            profiles = [profile for profile in profiles if profile]
            quality_score = min((float(p["rolling_good_ratio"]) for p in profiles), default=None)
            signal = EventSignal(
                self.camera_id,
                "ABANDONED_OBJECT",
                physical_id,
                True,
                frame_data.captured_at,
                now_s,
                float(event["association_score"]),
                {
                    "luggage": {
                        "physical_id": physical_id,
                        "source_track_ids": list(event["source_track_ids"]),
                        "bbox_xyxy": list(bag.latest_bbox),
                    },
                    "owner": {"person_track_id": int(event["owner_person_track_id"])},
                },
                {
                    "stationary_duration_s": max(0.0, now_s - float(event["stationary_start_s"])),
                    "owner_away_duration_s": max(0.0, now_s - float(event["owner_last_near_s"])),
                    "owner_association_score": float(event["association_score"]),
                    **({"luggage_quality_score": quality_score} if quality_score is not None else {}),
                },
                diagnostics={"source_core": "phase7c_core.infer_phase7c"},
            )
            self._active.add(physical_id)
            self._last_signals[physical_id] = signal
            signals.append(signal)
        for physical_id in self._active - seen:
            signals.append(self._end(physical_id, frame_data.captured_at, now_s))
            self._active.remove(physical_id)
            self._retired.add(physical_id)
        return signals

    def _stable_physical_id(self, source_ids: set[int]) -> str:
        for known_ids, physical_id in self._physical_ids:
            if known_ids & source_ids:
                known_ids.update(source_ids)
                return physical_id
        self._physical_counter += 1
        physical_id = f"LUG_{self._physical_counter:04d}"
        self._physical_ids.append((set(source_ids), physical_id))
        return physical_id

    def _end(self, physical_id: str, timestamp: str, now_s: float) -> EventSignal:
        previous = self._last_signals[physical_id]
        return EventSignal(
            previous.camera_id,
            previous.event_type,
            previous.entity_key,
            False,
            timestamp,
            now_s,
            previous.cv_confidence,
            previous.objects,
            previous.evidence,
            previous.spatial,
            previous.media,
            previous.diagnostics,
        )

    def reset(self) -> None:
        """Discard temporal rows so offline time cannot contribute to owner-away dwell."""
        self._rows.clear()
        self._active.clear()
        self._retired.clear()
        self._last_signals.clear()
        self._physical_ids.clear()
        self._physical_counter = 0
