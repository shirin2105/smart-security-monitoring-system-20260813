import time
from typing import Any

from app.common.enums import CameraStatus
from app.common.time_utils import calculate_duration_seconds, utc_now_iso


class CameraHealthMonitor:
    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        self.last_frame_at: str = utc_now_iso()
        self.decode_error_count: int = 0
        self.inference_error_count: int = 0
        self.frames_processed = 0
        self.frames_skipped = 0
        self.last_inference_latency_ms: float | None = None
        self.source: Any | None = None
        self._processing_started_at: float | None = None

    def attach_source(self, source: Any) -> None:
        self.source = source

    def record_processed(self, latency_ms: float | None = None) -> None:
        if self._processing_started_at is None:
            self._processing_started_at = time.monotonic()
        self.frames_processed += 1
        self.last_inference_latency_ms = latency_ms

    def record_skipped(self) -> None:
        self.frames_skipped += 1

    def update_frame_time(self, captured_at: str) -> None:
        self.last_frame_at = captured_at

    def record_decode_error(self) -> None:
        self.decode_error_count += 1

    def record_inference_error(self) -> None:
        self.inference_error_count += 1

    def get_status(self) -> dict[str, Any]:
        now_iso = utc_now_iso()
        age_seconds = calculate_duration_seconds(self.last_frame_at, now_iso)

        if age_seconds < 15.0:
            status = CameraStatus.HEALTHY
        elif 15.0 <= age_seconds <= 60.0:
            status = CameraStatus.DEGRADED
        else:
            status = CameraStatus.OFFLINE

        source = self.source
        elapsed_s = time.monotonic() - self._processing_started_at if self._processing_started_at is not None else 0.0
        processed_fps = self.frames_processed / elapsed_s if elapsed_s > 0 else 0.0
        return {
            "camera_id": self.camera_id,
            "last_frame_at": self.last_frame_at,
            "frame_age_seconds": age_seconds,
            "decode_error_count": self.decode_error_count,
            "inference_error_count": self.inference_error_count,
            "status": status.value,
            "connection_state": getattr(source, "connection_state", "CONNECTED"),
            "reconnect_count": int(getattr(source, "reconnect_count", 0)),
            "consecutive_read_failures": int(getattr(source, "consecutive_read_failures", 0)),
            "read_decode_errors": int(getattr(source, "read_decode_errors", 0)),
            "last_reconnect_at": getattr(source, "last_reconnect_at", None),
            "frames_received": int(getattr(source, "frames_received", 0)),
            "frames_processed": self.frames_processed,
            "frames_dropped_skipped": (int(getattr(source, "frames_dropped", 0)) + self.frames_skipped),
            "source_fps": float(getattr(source, "source_fps", 0.0)),
            "processed_fps": processed_fps,
            "last_inference_latency_ms": self.last_inference_latency_ms,
        }
