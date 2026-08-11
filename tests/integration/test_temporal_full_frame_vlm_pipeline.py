import numpy as np

from app.common.schemas import FrameData, StaticRegionObservation, VLMValidationResult
from app.events.abandoned_object import AbandonedObjectEngine


def test_temporal_pipeline_uses_full_scene_and_original_event_time():
    class Validator:
        def __init__(self):
            self.requests = []

        def validate_temporal(self, frames, region, event_time):
            self.requests.append((frames, region, event_time))
            return VLMValidationResult(verdict="unavailable", reason="provider_offline")

    validator = Validator()
    rules = {"abandoned_object": {"candidate_source": "static_regions", "owner_absent_seconds": 0,
        "temporal": {"enabled": True, "pre_seconds": 8, "post_seconds": 8,
                     "sample_fps": 1, "max_frames": 17}}}
    engine = AbandonedObjectEngine("cam", [], rules, region_validator=validator)
    region = StaticRegionObservation(region_id="scene-object", bbox=[2, 2, 8, 8],
        first_seen_at="2026-08-01T00:00:00Z", last_seen_at="2026-08-01T00:00:01Z",
        persistence_seconds=6, confidence=.85)
    events = []
    for second in range(10):
        engine.submit_static_regions([region])
        image = np.full((24, 32, 3), second, dtype=np.uint8)
        events.extend(engine.evaluate([], FrameData(camera_id="cam", frame_id=second + 1,
            captured_at=f"2026-08-01T00:00:{second:02d}Z", source_type="VIDEO",
            source_fps=25, inference_fps=25, image=image)))
    assert len(validator.requests) == 1
    frames, _, event_time = validator.requests[0]
    assert 1 <= len(frames) <= 17
    assert all(frame.image.shape == (24, 32, 3) for frame in frames)
    assert [frame.captured_at for frame in frames] == sorted(frame.captured_at for frame in frames)
    assert len(events) == 1
    assert events[0].detectedAt == event_time == "2026-08-01T00:00:01Z"
    metadata = engine.temporal_validation_metadata["scene-object"]
    assert metadata["decision_time"] == "2026-08-01T00:00:09Z"


def test_end_of_stream_discards_pending_window_without_partial_validation():
    class Validator:
        calls = 0
        def validate_temporal(self, *args):
            self.calls += 1
            raise AssertionError("EOS must not validate an incomplete post-roll")
    validator = Validator()
    engine = AbandonedObjectEngine("cam", [], {"abandoned_object": {
        "candidate_source": "static_regions", "owner_absent_seconds": 0,
        "temporal": {"enabled": True, "pre_seconds": 8, "post_seconds": 8}}},
        region_validator=validator)
    region = StaticRegionObservation(region_id="eos", bbox=[1, 1, 4, 4],
        first_seen_at="2026-08-01T00:00:00Z", last_seen_at="2026-08-01T00:00:01Z",
        persistence_seconds=6, confidence=.8)
    for second in range(4):
        engine.submit_static_regions([region])
        assert engine.evaluate([], FrameData(camera_id="cam", frame_id=second + 1,
            captured_at=f"2026-08-01T00:00:0{second}Z", source_type="VIDEO",
            source_fps=1, inference_fps=1, image=np.zeros((20, 30, 3), dtype=np.uint8))) == []
    assert engine.finalize() == ["eos"]
    assert validator.calls == 0
