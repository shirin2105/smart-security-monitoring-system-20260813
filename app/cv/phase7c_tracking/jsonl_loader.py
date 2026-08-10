from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterator


ALLOWED_CLASS_NAMES = {
    0: {"person"},
    1: {"backpack", "luggage"},
    2: {"handbag"},
    3: {"suitcase"},
}


@dataclass(frozen=True)
class TrackPoint:
    frame_index: int
    timestamp_s: float
    class_id: int
    class_name: str
    global_track_id: int
    local_track_id: int
    bbox_xyxy: tuple[float, float, float, float]
    confidence: float
    center_xy: tuple[float, float]


def _parse_point(row: dict, line_number: int) -> TrackPoint:
    try:
        class_id = int(row["class_id"])
        class_name = str(row["class_name"])
        bbox = tuple(float(value) for value in row["bbox_xyxy"])
        center = tuple(float(value) for value in row["center_xy"])
        if class_name not in ALLOWED_CLASS_NAMES.get(class_id, set()):
            raise ValueError("class_id/class_name mismatch")
        if len(bbox) != 4 or len(center) != 2:
            raise ValueError("invalid bbox or center shape")
        if bbox[2] < bbox[0] or bbox[3] < bbox[1]:
            raise ValueError("invalid bbox coordinates")
        return TrackPoint(
            frame_index=int(row["frame_index"]),
            timestamp_s=float(row["timestamp_s"]),
            class_id=class_id,
            class_name=class_name,
            global_track_id=int(row["global_track_id"]),
            local_track_id=int(row["local_track_id"]),
            bbox_xyxy=bbox,
            confidence=float(row["confidence"]),
            center_xy=center,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid Phase 7B JSONL row at line {line_number}: {exc}") from exc


def load_track_jsonl(path: str | Path) -> Iterator[TrackPoint]:
    """Yield validated observations without loading the whole video into memory."""
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line.strip():
                yield _parse_point(json.loads(line), line_number)
