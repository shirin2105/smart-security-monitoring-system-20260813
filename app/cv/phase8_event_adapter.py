from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable

from app.common.schemas import ArtifactData, FrameData
from app.evaluation.phase8_schema import PredictedEvent
from app.events.crowd import CrowdEventEngine
from app.events.intrusion import IntrusionEventEngine


class _NoEvidence:
    def capture_evidence(self, **_: Any) -> ArtifactData:
        return ArtifactData(available=False)


def _iso(timestamp_s: float) -> str:
    return datetime.fromtimestamp(timestamp_s, timezone.utc).isoformat().replace("+00:00", "Z")


def _seconds(timestamp: str) -> float:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp()


def _active_tracks(rows: Iterable[dict[str, Any]]) -> list[SimpleNamespace]:
    tracks = []
    for row in rows:
        box = [float(value) for value in row["bbox_xyxy"]]
        tracks.append(SimpleNamespace(
            track_id=int(row["global_track_id"]),
            class_name=str(row["class_name"]),
            latest_bbox=box,
            latest_foot_point=((box[0] + box[2]) / 2.0, box[3]),
            confidence=float(row["confidence"]),
        ))
    return tracks


def _rule_engines(camera_id: str, config: dict[str, Any]):
    intrusion = config["intrusion"]
    crowd = config["crowd"]
    engines = []
    if intrusion.get("enabled", True):
        engines.append(IntrusionEventEngine(
            camera_id,
            [{"camera_id": camera_id, "zone_id": intrusion.get("zone_id", "INTRUSION_ROI"),
              "polygon": intrusion["roi_polygon"], "enabled": True}],
            {"intrusion": {"dwell_seconds": intrusion.get("hold_s", 1.0),
                           "cooldown_seconds": intrusion.get("cooldown_s", 30.0)}},
            _NoEvidence(),
        ))
    if crowd.get("enabled", True):
        threshold = int(crowd["threshold"])
        engines.append(CrowdEventEngine(
            camera_id,
            [{"camera_id": camera_id, "zone_id": crowd.get("zone_id", "CROWD_ROI"),
              "polygon": crowd["roi_polygon"], "enabled": True}],
            {"crowd": {"count_threshold": threshold, "hold_seconds": crowd.get("hold_s", 3.0),
                       "release_threshold": crowd.get("release_threshold", max(0, threshold - 1)),
                       "cooldown_seconds": crowd.get("cooldown_s", 60.0)}},
            _NoEvidence(),
        ))
    return engines


def infer_rule_events(rows: list[dict[str, Any]], clip_id: str, camera_id: str,
                      config: dict[str, Any], fps_hint: float) -> list[PredictedEvent]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["frame_index"])].append(row)
    engines = _rule_engines(camera_id, config)
    predicted = []
    if not grouped:
        return []
    for frame_index in range(0, max(grouped) + 1):
        frame_rows = grouped.get(frame_index, [])
        timestamp_s = (max(float(row["timestamp_s"]) for row in frame_rows)
                       if frame_rows else frame_index / fps_hint)
        frame = FrameData(camera_id=camera_id, frame_id=frame_index, captured_at=_iso(timestamp_s),
                          source_type="VIDEO", source_fps=fps_hint, inference_fps=fps_hint)
        tracks = _active_tracks(frame_rows)
        for engine in engines:
            for candidate in engine.evaluate(tracks, frame):
                predicted.append(PredictedEvent(
                    clip_id=clip_id, camera_id=camera_id,
                    event_id=f"{clip_id}:{candidate.candidateId}",
                    event_type=candidate.eventType.value,
                    event_time_s=_seconds(candidate.detectedAt),
                    start_s=_seconds(candidate.firstSeenAt),
                    end_s=_seconds(candidate.lastSeenAt),
                    confidence=float(candidate.confidence),
                    evidence={"zone_id": candidate.zoneId, "track_ids": candidate.trackIds,
                              "source_pipeline": "DEIMv2-Phase7A+ByteTrack"},
                ))
    return predicted


def infer_abandoned_events(rows: list[dict[str, Any]], clip_id: str, camera_id: str,
                           config: dict[str, Any], fps_hint: float) -> list[PredictedEvent]:
    core_dir = Path(__file__).resolve().parents[2] / "kaggle_pipeline" / "phase7c_kernel"
    if str(core_dir) not in sys.path:
        sys.path.insert(0, str(core_dir))
    from phase7c_core import OwnerConfig, Phase7CConfig, StationaryConfig, infer_phase7c

    cfg = config["abandoned"]
    if not cfg.get("enabled", True):
        return []
    stationary = dict(cfg.get("stationary", {}))
    owner = dict(cfg.get("owner", {}))
    stationary.setdefault("hold_s", cfg.get("stationary_hold_s", 3.0))
    owner.setdefault("away_hold_s", cfg.get("owner_away_hold_s", 5.0))
    result = infer_phase7c(rows, Phase7CConfig(
        stationary=StationaryConfig(**stationary), owner=OwnerConfig(**owner),
        roi_polygon=cfg.get("valid_floor_roi_polygon"),
    ), fps_hint=fps_hint)
    output = []
    for event in result["events"]:
        output.append(PredictedEvent(
            clip_id=clip_id, camera_id=camera_id,
            event_id=f"{clip_id}:{event['event_id']}", event_type="ABANDONED_OBJECT",
            event_time_s=float(event["candidate_time_s"]),
            start_s=float(event["stationary_start_s"]), confidence=float(event["association_score"]),
            evidence={**event, "candidate_only": True,
                      "source_status": "ABANDONED_OBJECT_CANDIDATE",
                      "source_pipeline": "DEIMv2-Phase7A+ByteTrack+Phase7C"},
        ))
    return output


def infer_all_events(rows: list[dict[str, Any]], clip_id: str, camera_id: str,
                     config: dict[str, Any], fps_hint: float) -> list[PredictedEvent]:
    events = infer_rule_events(rows, clip_id, camera_id, config, fps_hint)
    events.extend(infer_abandoned_events(rows, clip_id, camera_id, config, fps_hint))
    for event in events:
        event.validate()
    return sorted(events, key=lambda event: (event.event_time_s, event.event_type, event.event_id))
