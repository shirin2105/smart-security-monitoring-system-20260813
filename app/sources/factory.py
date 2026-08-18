from __future__ import annotations

import os
from typing import Any

from app.sources.base import BaseVideoSource
from app.sources.mp4_source import MP4VideoSource
from app.sources.rtsp_source import RTSPVideoSource


def create_video_source(camera_config: dict[str, Any]) -> BaseVideoSource:
    """Create the source selected by a camera configuration without exposing its URI."""
    source_type = str(camera_config.get("source_type", "SIMULATED")).upper()
    camera_id = str(camera_config["camera_id"])
    uri = os.path.expandvars(str(camera_config.get("source_uri", "")))
    fps = float(camera_config.get("inference_fps", 5.0))
    if source_type in {"SIMULATED", "FILE", "MP4", "VIDEO"}:
        return MP4VideoSource(camera_id, uri, source_type, fps)
    if source_type in {"RTSP", "CAMERA", "LIVE"}:
        if not uri or "${" in uri:
            raise ValueError(f"RTSP source URI is not configured for camera {camera_id!r}")
        return RTSPVideoSource(camera_id, uri, fps, camera_config)
    raise ValueError(f"unsupported video source type {source_type!r} for camera {camera_id!r}")
