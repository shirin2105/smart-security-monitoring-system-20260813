"""Unit tests for the live-CV evidence clip publisher (no ffmpeg/network)."""

from app.cv.clip_publisher import build_event_candidate, clip_window
from app.cv.contracts.cv_event import CVEvent


def _make_event(event_id="evt-1", event_time_s=13.75, event_type="ABANDONED_OBJECT", camera_id="cam_01"):
    return CVEvent(
        schema_version="cv-event-v1",
        event_id=event_id,
        event_type=event_type,
        event_state="START",
        camera_id=camera_id,
        event_time="2026-01-01T00:00:13.750Z",
        event_time_s=event_time_s,
        cv_confidence=0.91,
        objects={"personCount": 2},
        evidence={},
        spatial={},
        media={},
        diagnostics={},
    )


def test_clip_window_clamps_negative_start_to_zero():
    start, end = clip_window(13.75, duration_s=60.0)
    assert start == 0.0
    assert end == 16.75


def test_clip_window_clamps_end_to_duration():
    start, end = clip_window(58.0, duration_s=60.0)
    assert start == 38.0
    assert end == 60.0


def test_clip_window_unbounded_when_duration_unknown():
    start, end = clip_window(13.75, duration_s=None)
    assert start == 0.0
    assert end == 16.75


def test_build_event_candidate_maps_video_timeline_and_clip():
    event = _make_event()
    candidate = build_event_candidate(event, event.event_time_s, "/evidence/evt-1.mp4")
    assert candidate["cameraId"] == "cam_01"
    assert candidate["eventType"] == "ABANDONED_OBJECT"
    assert candidate["detectedAt"].startswith("2026-01-01T00:00:13.75")
    assert candidate["firstSeenAt"] == candidate["detectedAt"]
    assert candidate["artifact"]["uri"] == "/evidence/evt-1.mp4"
    assert candidate["artifact"]["redactionStatus"] == "COMPLETE"
    assert candidate["artifact"]["contentType"] == "video/mp4"
    assert candidate["observations"]["personCount"] == 2


def test_build_event_candidate_without_clip_is_pending():
    event = _make_event()
    candidate = build_event_candidate(event, event.event_time_s, clip_url=None)
    assert candidate["artifact"]["uri"] is None
    assert candidate["artifact"]["available"] is False
    assert candidate["artifact"]["redactionStatus"] == "PENDING"
