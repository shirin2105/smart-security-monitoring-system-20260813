from app.common.schemas import FrameData
from app.cv.events.intrusion_adapter import IntrusionLifecycleAdapter
from app.cv.track_store import TrackState


def frame(second):
    return FrameData(camera_id="cam", frame_id=second,
                     captured_at=f"2026-01-01T00:00:{second:02d}Z",
                     source_type="VIDEO", source_fps=1, inference_fps=1)


def test_intrusion_exit_missing_track_and_reentry_lifecycle():
    adapter = IntrusionLifecycleAdapter(
        "cam", [{"camera_id": "cam", "zone_id": "z", "enabled": True,
                 "polygon": [[0, 0], [20, 0], [20, 20], [0, 20]]}],
        {"intrusion": {"dwell_seconds": 1}},
    )
    track = TrackState(1, "person", [1, 1, 5, 5], 0.9, frame(0).captured_at)
    assert adapter.evaluate([track], frame(0)) == []
    assert adapter.evaluate([track], frame(1))[0].active is True
    assert adapter.evaluate([], frame(2))[0].active is False
    assert adapter.evaluate([track], frame(3)) == []
    assert adapter.evaluate([track], frame(4))[0].active is True
