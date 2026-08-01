import pytest
from app.common.schemas import FrameData
from app.cv.track_store import TrackState
from app.events.crowd import CrowdEventEngine, CrowdState
from app.common.enums import EventType


def test_crowd_engine_state_machine_and_event_trigger():
    zones_config = [
        {
            "zone_id": "lobby_area",
            "camera_id": "cam_02",
            "polygon": [[0.0, 0.0], [1000.0, 0.0], [1000.0, 1000.0], [0.0, 1000.0]],
            "enabled": True,
        }
    ]
    rules_config = {
        "crowd": {
            "count_threshold": 3,  # Lower threshold for unit test (3 people)
            "hold_seconds": 2.0,   # 2 seconds hold time
            "release_threshold": 1,
            "cooldown_seconds": 30,
        }
    }

    engine = CrowdEventEngine("cam_02", zones_config, rules_config)

    t1_iso = "2026-07-30T10:00:00Z"
    t2_iso = "2026-07-30T10:00:03Z"  # 3s elapsed (> 2.0s hold)

    # 3 person tracks inside ROI polygon
    tracks = [
        TrackState(track_id=1, class_name="person", bbox=[100, 100, 150, 150], confidence=0.9, timestamp=t1_iso),
        TrackState(track_id=2, class_name="person", bbox=[200, 200, 250, 250], confidence=0.9, timestamp=t1_iso),
        TrackState(track_id=3, class_name="person", bbox=[300, 300, 350, 350], confidence=0.9, timestamp=t1_iso),
    ]

    frame1 = FrameData(
        camera_id="cam_02", frame_id=1, captured_at=t1_iso, source_type="SIMULATED", source_fps=5.0, inference_fps=5.0
    )

    # Frame 1: Count = 3 >= threshold -> THRESHOLD_PENDING (no candidate yet)
    candidates1 = engine.evaluate(tracks, frame1)
    assert len(candidates1) == 0
    assert engine.zone_trackers["lobby_area"].current_state == CrowdState.THRESHOLD_PENDING

    # Frame 2: 3 seconds elapsed -> CROWD_ACTIVE -> Event Candidate Generated!
    for t in tracks:
        t.last_seen_at = t2_iso

    frame2 = FrameData(
        camera_id="cam_02", frame_id=2, captured_at=t2_iso, source_type="SIMULATED", source_fps=5.0, inference_fps=5.0
    )

    candidates2 = engine.evaluate(tracks, frame2)
    assert len(candidates2) == 1
    assert candidates2[0].eventType == EventType.CROWD_THRESHOLD
    assert candidates2[0].trackCount == 3
    assert candidates2[0].observations.personCount == 3
    assert engine.zone_trackers["lobby_area"].current_state == CrowdState.CROWD_ACTIVE
