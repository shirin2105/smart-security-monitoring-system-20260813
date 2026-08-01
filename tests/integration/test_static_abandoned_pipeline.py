from app.common.schemas import FrameData, StaticRegionObservation
from app.cv.track_store import TrackState
from app.events.abandoned_object import AbandonedObjectEngine


def test_person_only_tracks_can_contextualize_unclassified_region():
    engine = AbandonedObjectEngine("cam", [], {"abandoned_object": {"candidate_source": "static_regions", "owner_absent_seconds": 0}})
    region = StaticRegionObservation(region_id="unknown-object", bbox=[10, 10, 30, 30], first_seen_at="2026-08-01T00:00:00Z", last_seen_at="2026-08-01T00:00:02Z", persistence_seconds=2, confidence=.9)
    frame = lambda i, ts: FrameData(camera_id="cam", frame_id=i, captured_at=ts, source_type="VIDEO", source_fps=1, inference_fps=1)
    engine.submit_static_regions([region])
    engine.evaluate([TrackState(1, "person", [10, 0, 30, 20], .9, "2026-08-01T00:00:02Z")], frame(1, "2026-08-01T00:00:02Z"))
    engine.submit_static_regions([region])
    engine.evaluate([], frame(2, "2026-08-01T00:00:03Z"))
    engine.submit_static_regions([region])
    assert len(engine.evaluate([], frame(3, "2026-08-01T00:00:04Z"))) == 1
