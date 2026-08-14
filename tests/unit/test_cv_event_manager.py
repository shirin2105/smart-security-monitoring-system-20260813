from dataclasses import replace

import pytest

from app.cv.event_manager import CVEventManager
from app.cv.events.event_signal import EventSignal


def intrusion(active=True, time_s=1.0, duration=2.0):
    return EventSignal(
        "cam-1", "ZONE_INTRUSION", "zone-a:7", active,
        f"2026-01-01T00:00:{int(time_s):02d}Z", time_s, 0.9,
        {"persons": [{"track_id": 7, "bbox_xyxy": [0, 0, 10, 10]}]},
        {"zone_id": "zone-a", "inside_duration_s": duration},
    )


def test_start_update_end_use_one_id_and_duplicates_are_suppressed():
    manager = CVEventManager("cam-1", update_interval_s=1.0)
    start = manager.process(intrusion())
    assert start.event_state == "START"
    assert manager.process(intrusion(time_s=2.0)) is None
    update = manager.process(intrusion(time_s=3.0, duration=4.0))
    end = manager.process(intrusion(active=False, time_s=4.0, duration=4.0))
    assert [update.event_state, end.event_state] == ["UPDATE", "END"]
    assert start.event_id == update.event_id == end.event_id
    assert manager.process(intrusion(active=False, time_s=5.0)) is None


def test_reentry_gets_new_id_and_instances_are_isolated():
    first = CVEventManager("cam-1").process(intrusion())
    manager = CVEventManager("cam-1")
    start = manager.process(intrusion())
    manager.process(intrusion(active=False, time_s=2.0))
    reentry = manager.process(intrusion(time_s=3.0))
    assert start.event_id != reentry.event_id
    assert first.event_id != start.event_id


def test_rejects_time_reversal_and_wrong_camera():
    manager = CVEventManager("cam-1")
    manager.process(intrusion(time_s=2.0))
    with pytest.raises(ValueError, match="backwards"):
        manager.process(intrusion(time_s=1.0))
    with pytest.raises(ValueError, match="camera_id"):
        manager.process(replace(intrusion(time_s=3.0), camera_id="cam-2"))
