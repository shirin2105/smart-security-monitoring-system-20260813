from datetime import datetime, timedelta, timezone
from typing import Optional


def utc_now_iso() -> str:
    """Return current timestamp in UTC ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso_timestamp(iso_str: str) -> datetime:
    """Parse ISO 8601 timestamp string into tz-aware datetime."""
    if iso_str.endswith("Z"):
        iso_str = iso_str[:-1] + "+00:00"
    return datetime.fromisoformat(iso_str)


def calculate_duration_seconds(start_iso: str, end_iso: str) -> float:
    """Calculate difference in seconds between two ISO 8601 timestamp strings."""
    t1 = parse_iso_timestamp(start_iso)
    t2 = parse_iso_timestamp(end_iso)
    return max(0.0, (t2 - t1).total_seconds())


def video_timestamp_iso(start_iso: str, frame_offset: int, source_fps: float) -> str:
    """Return deterministic UTC media time for a zero-based frame offset."""
    start = parse_iso_timestamp(start_iso)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    fps = source_fps if source_fps and source_fps > 0 else 25.0
    timestamp = start.astimezone(timezone.utc) + timedelta(seconds=max(0, frame_offset) / fps)
    return timestamp.isoformat(timespec="microseconds").replace("+00:00", "Z")
