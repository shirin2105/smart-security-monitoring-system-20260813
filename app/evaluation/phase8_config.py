from __future__ import annotations

import json
from math import isfinite
from pathlib import Path
from typing import Any


def load_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def validate_polygon(name: str, value: Any) -> None:
    if not isinstance(value, list) or len(value) < 3:
        raise ValueError(f"{name} must contain at least three points")
    for point in value:
        if not isinstance(point, list) or len(point) != 2:
            raise ValueError(f"{name} points must be [x, y]")
        coordinates = (float(point[0]), float(point[1]))
        if not all(isfinite(value) for value in coordinates):
            raise ValueError(f"{name} coordinates must be finite")


def validate_camera_config(payload: dict[str, Any], camera_id: str) -> dict[str, Any]:
    if payload.get("camera_id") != camera_id:
        raise ValueError(f"camera_id mismatch: expected {camera_id}")
    if payload.get("inference_profile") not in {"full640", "tile768_overlap20"}:
        raise ValueError("inference_profile must be full640 or tile768_overlap20")
    for section, polygon_key in (
        ("intrusion", "roi_polygon"),
        ("crowd", "roi_polygon"),
        ("abandoned", "valid_floor_roi_polygon"),
    ):
        cfg = payload.get(section)
        if not isinstance(cfg, dict):
            raise ValueError(f"missing camera section: {section}")
        if cfg.get("enabled", True):
            validate_polygon(f"{section}.{polygon_key}", cfg.get(polygon_key))
    crowd = payload["crowd"]
    if crowd.get("enabled", True) and int(crowd.get("threshold", 0)) < 1:
        raise ValueError("crowd.threshold must be >= 1")
    for section, key in (
        ("intrusion", "hold_s"),
        ("crowd", "hold_s"),
        ("abandoned", "stationary_hold_s"),
        ("abandoned", "owner_away_hold_s"),
    ):
        if not payload[section].get("enabled", True):
            continue
        value = float(payload[section].get(key, -1))
        if not isfinite(value) or value < 0:
            raise ValueError(f"{section}.{key} must be non-negative")
    return payload


def validate_manifest(payload: dict[str, Any], require_validation_size: bool = True) -> list[dict[str, Any]]:
    clips = payload.get("clips")
    if not isinstance(clips, list):
        raise ValueError("manifest.clips must be an array")
    if require_validation_size and not 20 <= len(clips) <= 30:
        raise ValueError("Phase 8 manifest must contain 20-30 clips")
    ids: set[str] = set()
    has_positive = has_negative = False
    for clip in clips:
        required = {"clip_id", "video_path", "camera_id", "camera_config_path", "scenario_tags"}
        missing = required - set(clip)
        if missing:
            raise ValueError(f"manifest clip missing fields: {sorted(missing)}")
        clip_id = str(clip["clip_id"])
        if clip_id in ids:
            raise ValueError(f"duplicate clip_id={clip_id}")
        ids.add(clip_id)
        if not isinstance(clip["scenario_tags"], list):
            raise ValueError(f"scenario_tags must be an array: {clip_id}")
        tags = [str(tag).lower() for tag in clip["scenario_tags"]]
        has_positive |= any("positive" in tag for tag in tags)
        has_negative |= any("negative" in tag for tag in tags)
        duration = float(clip.get("expected_duration_s", 0))
        if duration <= 0:
            raise ValueError(f"expected_duration_s must be positive: {clip_id}")
    if clips and not (has_positive and has_negative):
        raise ValueError("manifest must include positive and negative scenarios")
    if require_validation_size:
        aliases = {"ZONE_INTRUSION": ("intrusion",), "CROWD_THRESHOLD": ("crowd",),
                   "ABANDONED_OBJECT": ("abandoned", "ao_")}
        for event_type, names in aliases.items():
            event_tags = [str(tag).lower() for clip in clips for tag in clip["scenario_tags"]
                          if any(name in str(tag).lower() for name in names)]
            if not any("positive" in tag for tag in event_tags) or not any(
                    "negative" in tag for tag in event_tags):
                raise ValueError(f"manifest needs positive and negative coverage for {event_type}")
    return clips
