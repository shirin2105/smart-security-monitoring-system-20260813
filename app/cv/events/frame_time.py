from __future__ import annotations

from typing import Any

from app.common.time_utils import parse_iso_timestamp

LIVE_SOURCE_TYPES = {"RTSP", "CAMERA", "LIVE"}


def frame_time_seconds(frame_data: Any) -> float:
    """Return a monotonic event clock for file and live source semantics."""
    if str(frame_data.source_type).upper() in LIVE_SOURCE_TYPES:
        return parse_iso_timestamp(frame_data.captured_at).timestamp()
    fps = max(float(frame_data.source_fps), 1e-9)
    return max(0.0, float(frame_data.frame_id - 1) / fps)
