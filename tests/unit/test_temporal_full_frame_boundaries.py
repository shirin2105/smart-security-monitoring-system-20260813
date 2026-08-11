import numpy as np

from app.common.schemas import FrameData, StaticRegionObservation, VLMValidationResult
from app.events.abandoned_object import AbandonedObjectEngine


def _frame(second: int) -> FrameData:
    return FrameData(
        camera_id="cam",
        frame_id=second + 1,
        captured_at=f"2026-08-01T00:00:{second:02d}Z",
        source_type="VIDEO",
        source_fps=25,
        inference_fps=25,
        image=np.full((24, 32, 3), second, dtype=np.uint8),
    )


def test_exact_inclusive_window_and_one_call_per_region():
    class Validator:
        def __init__(self):
            self.calls = []

        def validate_temporal(self, frames, region, event_time):
            self.calls.append((region.region_id, event_time, frames))
            return VLMValidationResult(verdict="accepted", reason="test")

    validator = Validator()
    engine = AbandonedObjectEngine("cam", [], {"abandoned_object": {
        "candidate_source": "static_regions", "owner_absent_seconds": 8,
        "temporal": {"enabled": True, "pre_seconds": 8, "post_seconds": 8,
                     "sample_fps": 1, "max_frames": 17},
    }}, region_validator=validator)
    regions = [StaticRegionObservation(
        region_id=region_id, bbox=[0, 0, 5, 5],
        first_seen_at="2026-08-01T00:00:00Z",
        last_seen_at="2026-08-01T00:00:08Z",
        persistence_seconds=6, confidence=.8,
    ) for region_id in ("left", "right")]

    events = []
    for second in range(17):
        engine.submit_static_regions(regions)
        events.extend(engine.evaluate([], _frame(second)))
        if second < 16:
            assert validator.calls == []

    assert len(validator.calls) == 2
    assert {call[0] for call in validator.calls} == {"left", "right"}
    expected = [f"2026-08-01T00:00:{second:02d}Z" for second in range(17)]
    for _, event_time, frames in validator.calls:
        assert event_time == "2026-08-01T00:00:08Z"
        assert [frame.captured_at for frame in frames] == expected
        assert [int(frame.image[0, 0, 0]) for frame in frames] == list(range(17))
    assert len(events) == 2
    assert all(event.detectedAt == "2026-08-01T00:00:08Z" for event in events)
    assert len(engine._temporal_frames) <= 18
