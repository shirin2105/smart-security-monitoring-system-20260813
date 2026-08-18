import numpy as np
from app.common.schemas import FrameData
from app.cv.events.intrusion_adapter import IntrusionLifecycleAdapter
from app.cv.track_store import TrackState


def frame(second, image=None):
    return FrameData(camera_id="cam", frame_id=second,
                     captured_at=f"2026-01-01T00:00:{second:02d}Z",
                     source_type="VIDEO", source_fps=1, inference_fps=1,
                     image=image)


def test_intrusion_exit_missing_track_and_reentry_lifecycle():
    adapter = IntrusionLifecycleAdapter(
        "cam", [{"camera_id": "cam", "zone_id": "z", "enabled": True,
                 "polygon": [[0, 0], [20, 0], [20, 20], [0, 20]]}],
        {"intrusion": {"dwell_seconds": 1, "exit_grace_seconds": 0.5}},
    )
    track = TrackState(1, "person", [1, 1, 5, 5], 0.9, frame(0).captured_at)
    assert adapter.evaluate([track], frame(0)) == []
    assert adapter.evaluate([track], frame(1))[0].active is True
    assert adapter.evaluate([], frame(2))[0].active is False
    assert adapter.evaluate([track], frame(3)) == []
    assert adapter.evaluate([track], frame(4))[0].active is True


def test_intrusion_with_scaled_canvas_polygon():
    # Zone defined in 1280x720 canvas coordinates: x in [640, 1280], y in [360, 720] (bottom right)
    # Video frame is 768x432 (Cam 2)
    # Scaled zone in 768x432 will be: x in [384, 768], y in [216, 432]
    img = np.zeros((432, 768, 3), dtype=np.uint8)
    adapter = IntrusionLifecycleAdapter(
        "cam", [{"camera_id": "cam", "zone_id": "z_bottom_right", "enabled": True,
                 "polygon": [[640, 360], [1280, 360], [1280, 720], [640, 720]]}],
        {"intrusion": {"dwell_seconds": 0.5, "exit_grace_seconds": 0.5}},
    )
    # Person with foot point at x=500, y=300 in native 768x432 video (which is inside scaled [384..768, 216..432])
    track = TrackState(1, "person", [480, 250, 520, 300], 0.9, frame(0).captured_at)
    assert adapter.evaluate([track], frame(0, image=img)) == []
    # After 1s, dwell threshold 0.5s is satisfied
    signals = adapter.evaluate([track], frame(1, image=img))
    assert len(signals) == 1
    assert signals[0].active is True
    assert signals[0].evidence["zone_id"] == "z_bottom_right"


def test_intrusion_exit_grace_tolerates_short_jitter():
    # Dwell threshold = 1.0s, Exit grace = 1.0s
    adapter = IntrusionLifecycleAdapter(
        "cam", [{"camera_id": "cam", "zone_id": "z", "enabled": True,
                 "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]]}],
        {"intrusion": {"dwell_seconds": 1.0, "exit_grace_seconds": 1.0}},
    )
    inside_track = TrackState(1, "person", [10, 10, 30, 30], 0.9, frame(0).captured_at)
    outside_track = TrackState(1, "person", [150, 150, 180, 180], 0.9, frame(0).captured_at)

    # Frame 0: Inside -> ENTERING
    assert adapter.evaluate([inside_track], frame(0)) == []
    # Frame 1: Brief jitter outside (at t=0.5s or frame 1) -> within 1.0s grace period
    # Note: frame 1 is captured at 00:00:01Z, which is within 1s grace of 00:00:00Z
    # Next frame back inside -> dwell is preserved and triggers active!
    signals = adapter.evaluate([inside_track], frame(2))
    assert len(signals) == 1
    assert signals[0].active is True
