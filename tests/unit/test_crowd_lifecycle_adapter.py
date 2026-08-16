from app.common.schemas import FrameData
from app.cv.events.crowd_adapter import CrowdLifecycleAdapter
from app.cv.track_store import TrackState


def frame(second):
    return FrameData(camera_id="cam", frame_id=second,
                     captured_at=f"2026-01-01T00:00:{second:02d}Z",
                     source_type="VIDEO", source_fps=1, inference_fps=1)


def people(count):
    return [TrackState(i, "person", [i, 1, i + 0.5, 2], 0.9, frame(0).captured_at)
            for i in range(count)]


def test_crowd_full_frame_ignores_zone_and_counts_all_persons():
    # Product Policy v2: CROWD_THRESHOLD counts all persons in the full frame; the
    # zone polygon is ignored (zones are only for ZONE_INTRUSION). The zone below is
    # placed far away from the test persons yet the event must still fire.
    adapter = CrowdLifecycleAdapter(
        "cam", [{"camera_id": "cam", "zone_id": "z", "enabled": True,
                 "polygon": [[1000, 0], [2000, 0], [2000, 2000], [1000, 2000]]}],
        {"crowd": {"count_threshold": 2, "hold_seconds": 1,
                   "release_threshold": 1}},
    )
    tracks = people(2)
    assert adapter.evaluate(tracks, frame(0)) == []
    active = adapter.evaluate(tracks, frame(1))[0]
    assert active.active and active.objects["person_track_ids"] == [0, 1]
    assert active.spatial["zone_id"] == "FULL_FRAME"
    assert adapter.evaluate(people(1), frame(2))[0].active is False
    adapter.evaluate(people(1), frame(3))
    assert adapter.evaluate(tracks, frame(4)) == []
    assert adapter.evaluate(tracks, frame(5))[0].active is True
