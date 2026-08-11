from typing import Dict, Any
from app.common.enums import CameraStatus
from app.common.time_utils import utc_now_iso, calculate_duration_seconds


class CameraHealthMonitor:
    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        self.last_frame_at: str = utc_now_iso()
        self.decode_error_count: int = 0
        self.inference_error_count: int = 0

    def update_frame_time(self, captured_at: str) -> None:
        self.last_frame_at = captured_at

    def record_decode_error(self) -> None:
        self.decode_error_count += 1

    def record_inference_error(self) -> None:
        self.inference_error_count += 1

    def get_status(self) -> Dict[str, Any]:
        now_iso = utc_now_iso()
        age_seconds = calculate_duration_seconds(self.last_frame_at, now_iso)
        
        if age_seconds < 15.0:
            status = CameraStatus.HEALTHY
        elif 15.0 <= age_seconds <= 60.0:
            status = CameraStatus.DEGRADED
        else:
            status = CameraStatus.OFFLINE

        return {
            "camera_id": self.camera_id,
            "last_frame_at": self.last_frame_at,
            "frame_age_seconds": age_seconds,
            "decode_error_count": self.decode_error_count,
            "inference_error_count": self.inference_error_count,
            "status": status.value,
        }
