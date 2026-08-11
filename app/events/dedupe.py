from typing import Dict, Optional
from app.common.time_utils import calculate_duration_seconds, utc_now_iso


class EventDedupeManager:
    def __init__(self, cooldown_seconds: float = 30.0):
        self.cooldown_seconds = cooldown_seconds
        self.last_emitted: Dict[str, str] = {}  # dedupe_key -> timestamp_iso

    def generate_dedupe_key(self, camera_id: str, event_type: str, zone_id: str, track_id: int) -> str:
        return f"{camera_id}:{event_type}:{zone_id}:{track_id}"

    def generate_candidate_id(self, camera_id: str, event_type: str, zone_id: str, track_id: int, timestamp_iso: str) -> str:
        ts_clean = timestamp_iso.replace(":", "").replace("-", "").replace(".", "")
        return f"{camera_id}-{event_type}-{zone_id}-track{track_id}-{ts_clean}"

    def should_emit(self, dedupe_key: str, timestamp_iso: str) -> bool:
        if dedupe_key not in self.last_emitted:
            return True
        last_ts = self.last_emitted[dedupe_key]
        elapsed = calculate_duration_seconds(last_ts, timestamp_iso)
        return elapsed >= self.cooldown_seconds

    def record_emitted(self, dedupe_key: str, timestamp_iso: str) -> None:
        self.last_emitted[dedupe_key] = timestamp_iso
