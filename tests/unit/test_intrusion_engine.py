import pytest
from app.common.schemas import FrameData
from app.cv.track_store import TrackState
from app.events.intrusion import IntrusionEventEngine
from app.common.time_utils import utc_now_iso


def test_intrusion_dwell_time_trigger():
    zones_config = [
        {
            "zone_id": "restricted_gate",
            "camera_id": "cam_01",
            "polygon": [[0.0, 0.0], [500.0, 0.0], [500.0, 500.0], [0.0, 500.0]],
            "enabled": True,
        }
    ]
    rules_config = {"intrusion": {"dwell_seconds": 1.0, "cooldown_seconds": 30}}

    engine = IntrusionEventEngine("cam_01", zones_config, rules_config)

    # Person track at foot point (250, 250) - inside polygon
    t1_iso = "2026-07-30T10:00:00Z"
    t2_iso = "2026-07-30T10:00:02Z"  # 2.0s elapsed (dwell > 1.0s)

    track = TrackState(track_id=1, class_name="person", bbox=[200, 200, 300, 250], confidence=0.9, timestamp=t1_iso)
    frame1 = FrameData(
        camera_id="cam_01", frame_id=1, captured_at=t1_iso, source_type="SIMULATED", source_fps=5.0, inference_fps=5.0
    )

    # Frame 1: Dwell = 0s -> INSIDE_PENDING (no event yet)
    candidates1 = engine.evaluate([track], frame1)
    assert len(candidates1) == 0

    # Frame 2: Dwell = 2.0s -> INTRUSION_ACTIVE -> Event Candidate Generated!
    track.update(bbox=[200, 200, 300, 250], confidence=0.9, timestamp=t2_iso)
    frame2 = FrameData(
        camera_id="cam_01", frame_id=2, captured_at=t2_iso, source_type="SIMULATED", source_fps=5.0, inference_fps=5.0
    )

    candidates2 = engine.evaluate([track], frame2)
    assert len(candidates2) == 1
    assert candidates2[0].eventType == "ZONE_INTRUSION"
    assert candidates2[0].trackIds == [1]
    assert candidates2[0].observations.dwellSeconds >= 1.0
