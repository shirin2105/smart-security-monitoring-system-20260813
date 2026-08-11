import pytest
import numpy as np
from app.common.schemas import FrameData, StaticRegionObservation
from app.cv.track_store import TrackState
from app.events.abandoned_object import AbandonedObjectEngine, AbandonedObjectState
from app.common.enums import EventType
from app.common.schemas import VLMValidationResult


def test_abandoned_object_trigger_flow():
    zones_config = []
    rules_config = {
        "abandoned_object": {
            "stationary_seconds": 1.0,  # 1s stationary threshold
            "stationary_pixel_threshold": 15.0,
            "owner_association_distance": 150.0,
            "owner_absent_seconds": 1.0,  # 1s owner absent threshold
            "cooldown_seconds": 30,
        }
    }

    engine = AbandonedObjectEngine("cam_01", zones_config, rules_config)

    t1_iso = "2026-07-30T10:00:00Z"
    t2_iso = "2026-07-30T10:00:01Z"
    t3_iso = "2026-07-30T10:00:02Z"
    t4_iso = "2026-07-30T10:00:04Z"
    t5_iso = "2026-07-30T10:00:06Z"

    # Person track at (100, 100) and Backpack object track at (105, 105)
    person_track = TrackState(track_id=1, class_name="person", bbox=[90, 80, 110, 120], confidence=0.9, timestamp=t1_iso)
    backpack_track = TrackState(track_id=10, class_name="backpack", bbox=[105, 105, 125, 125], confidence=0.88, timestamp=t1_iso)

    # Frame 1 (t1): Object appears (frame_id=2 > 1) -> MOVING -> center history recorded
    frame1 = FrameData(camera_id="cam_01", frame_id=2, captured_at=t1_iso, source_type="SIMULATED", source_fps=5.0, inference_fps=5.0)
    engine.evaluate([person_track, backpack_track], frame1)

    # Frame 2 (t2): Stationary 1s -> STATIONARY_PENDING
    backpack_track.update(bbox=[105, 105, 125, 125], confidence=0.88, timestamp=t2_iso)
    frame2 = FrameData(camera_id="cam_01", frame_id=3, captured_at=t2_iso, source_type="SIMULATED", source_fps=5.0, inference_fps=5.0)
    engine.evaluate([person_track, backpack_track], frame2)

    # Frame 3 (t3): Stationary >= 1.0s -> STATIONARY
    backpack_track.update(bbox=[105, 105, 125, 125], confidence=0.88, timestamp=t3_iso)
    frame3 = FrameData(camera_id="cam_01", frame_id=4, captured_at=t3_iso, source_type="SIMULATED", source_fps=5.0, inference_fps=5.0)
    engine.evaluate([person_track, backpack_track], frame3)

    # Frame 4 (t4): Person #1 moves away to (800, 800) -> OWNER_LEFT_PENDING
    person_far = TrackState(track_id=1, class_name="person", bbox=[790, 780, 810, 820], confidence=0.9, timestamp=t4_iso)
    backpack_track.update(bbox=[105, 105, 125, 125], confidence=0.88, timestamp=t4_iso)
    frame4 = FrameData(camera_id="cam_01", frame_id=5, captured_at=t4_iso, source_type="SIMULATED", source_fps=5.0, inference_fps=5.0)
    engine.evaluate([person_far, backpack_track], frame4)

    # Frame 5 (t5): Owner absent >= 1.0s -> ABANDONED_CANDIDATE triggered!
    backpack_track.update(bbox=[105, 105, 125, 125], confidence=0.88, timestamp=t5_iso)
    frame5 = FrameData(camera_id="cam_01", frame_id=6, captured_at=t5_iso, source_type="SIMULATED", source_fps=5.0, inference_fps=5.0)
    candidates5 = engine.evaluate([person_far, backpack_track], frame5)

    assert len(candidates5) == 1
    assert candidates5[0].eventType == EventType.ABANDONED_OBJECT
    assert candidates5[0].trackIds == [10]
    assert candidates5[0].observations.stationarySeconds >= 1.0
    assert candidates5[0].observations.ownerAbsentSeconds >= 1.0


def test_static_region_emits_once_after_nearby_person_leaves():
    rules = {"abandoned_object": {"candidate_source": "static_regions", "owner_association_distance": 100, "owner_absent_seconds": 1}}
    engine = AbandonedObjectEngine("cam_01", [], rules)
    person = TrackState(1, "person", [45, 20, 55, 50], .9, "2026-08-01T00:00:00Z")
    region = StaticRegionObservation(region_id="r1", bbox=[40, 40, 60, 60], first_seen_at="2026-08-01T00:00:00Z", last_seen_at="2026-08-01T00:00:02Z", persistence_seconds=2, confidence=.8)
    engine.submit_static_regions([region])
    assert engine.evaluate([person], FrameData(camera_id="cam_01", frame_id=1, captured_at="2026-08-01T00:00:02Z", source_type="SIMULATED", source_fps=1, inference_fps=1)) == []
    engine.submit_static_regions([region])
    engine.evaluate([], FrameData(camera_id="cam_01", frame_id=2, captured_at="2026-08-01T00:00:03Z", source_type="SIMULATED", source_fps=1, inference_fps=1))
    engine.submit_static_regions([region])
    events = engine.evaluate([], FrameData(camera_id="cam_01", frame_id=3, captured_at="2026-08-01T00:00:04Z", source_type="SIMULATED", source_fps=1, inference_fps=1))
    assert len(events) == 1 and events[0].trackIds == []
    engine.submit_static_regions([region])
    assert engine.evaluate([], FrameData(camera_id="cam_01", frame_id=4, captured_at="2026-08-01T00:00:05Z", source_type="SIMULATED", source_fps=1, inference_fps=1)) == []


def test_static_region_validation_is_cached_and_unavailable_fails_open():
    class Validator:
        calls = 0
        def validate(self, crop, region):
            self.calls += 1
            return VLMValidationResult(verdict="unavailable", reason="offline")
    validator = Validator()
    engine = AbandonedObjectEngine("cam", [], {"abandoned_object": {
        "candidate_source": "static_regions", "owner_absent_seconds": 0}}, region_validator=validator)
    region = StaticRegionObservation(region_id="stable-id", bbox=[0, 0, 10, 10],
        first_seen_at="2026-08-01T00:00:00Z", last_seen_at="2026-08-01T00:00:01Z",
        persistence_seconds=1, confidence=.8)
    for frame_id in (1, 2):
        engine.submit_static_regions([region])
        events = engine.evaluate([], FrameData(camera_id="cam", frame_id=frame_id,
            captured_at=f"2026-08-01T00:00:0{frame_id}Z", source_type="VIDEO",
            source_fps=1, inference_fps=1, image=np.ones((12, 12, 3), dtype=np.uint8)))
    assert len(events) == 1
    assert "stable-id" in events[0].candidateId
    assert validator.calls == 1


@pytest.mark.parametrize("verdict,expected", [("accepted", 1), ("unavailable", 1), ("rejected", 0)])
def test_temporal_region_waits_for_postroll_and_preserves_candidate_time(verdict, expected):
    class Validator:
        def __init__(self): self.calls = []
        def validate(self, crop, region): raise AssertionError("crop path must not run")
        def validate_temporal(self, frames, region, event_time):
            self.calls.append((frames, event_time))
            return VLMValidationResult(verdict=verdict, reason="test")
    validator = Validator()
    engine = AbandonedObjectEngine("cam", [], {"abandoned_object": {
        "candidate_source": "static_regions", "owner_absent_seconds": 0,
        "temporal": {"enabled": True, "pre_seconds": 8, "post_seconds": 8,
                     "sample_fps": 1, "max_frames": 17}}}, region_validator=validator)
    region = StaticRegionObservation(region_id="r", bbox=[0, 0, 5, 5],
        first_seen_at="2026-08-01T00:00:00Z", last_seen_at="2026-08-01T00:00:01Z",
        persistence_seconds=6, confidence=.8)
    emitted = []
    for second in range(18):
        engine.submit_static_regions([region] if second <= 2 else [])
        emitted += engine.evaluate([], FrameData(camera_id="cam", frame_id=second + 1,
            captured_at=f"2026-08-01T00:00:{second:02d}Z", source_type="VIDEO",
            source_fps=10, inference_fps=10, image=np.full((12, 18, 3), second, dtype=np.uint8)))
        if second < 9:
            assert validator.calls == []
    assert len(validator.calls) == 1
    frames, event_time = validator.calls[0]
    assert event_time == "2026-08-01T00:00:01Z"
    assert [frame.captured_at for frame in frames] == [f"2026-08-01T00:00:{s:02d}Z" for s in range(10)]
    assert len(emitted) == expected
    if emitted:
        assert emitted[0].detectedAt == event_time
        assert emitted[0].lastSeenAt == event_time
        assert event_time.replace(":", "").replace("-", "") in emitted[0].candidateId
    assert len(engine._temporal_frames) <= 18


def test_temporal_missing_images_finishes_unavailable_and_cleans_pending():
    engine = AbandonedObjectEngine("cam", [], {"abandoned_object": {
        "candidate_source": "static_regions", "owner_absent_seconds": 0,
        "temporal": {"enabled": True, "pre_seconds": 8, "post_seconds": 8}}})
    region = StaticRegionObservation(region_id="no-image", bbox=[0, 0, 5, 5],
        first_seen_at="2026-08-01T00:00:00Z", last_seen_at="2026-08-01T00:00:01Z",
        persistence_seconds=6, confidence=.8)
    events = []
    for second in range(10):
        engine.submit_static_regions([region] if second < 2 else [])
        events.extend(engine.evaluate([], FrameData(camera_id="cam", frame_id=second + 1,
            captured_at=f"2026-08-01T00:00:{second:02d}Z", source_type="VIDEO",
            source_fps=1, inference_fps=1, image=None)))
    assert len(events) == 1
    assert events[0].detectedAt == "2026-08-01T00:00:01Z"
    assert engine.region_validation_results["no-image"].verdict == "unavailable"
    assert "no-image" not in engine.region_states


def test_temporal_4k_frames_are_full_scene_resized_and_memory_bounded():
    engine = AbandonedObjectEngine("cam", [], {"abandoned_object": {
        "candidate_source": "static_regions", "temporal": {"enabled": True,
        "buffer_max_dimension": 480, "buffer_byte_ceiling": 3_000_000}}})
    for second in range(17):
        engine.submit_static_regions([])
        engine.evaluate([], FrameData(camera_id="cam", frame_id=second + 1,
            captured_at=f"2026-08-01T00:00:{second:02d}Z", source_type="VIDEO",
            source_fps=1, inference_fps=1,
            image=np.zeros((2160, 3840, 3), dtype=np.uint8)))
    assert engine._temporal_frames
    assert all(frame.image.shape[:2] == (270, 480) for frame in engine._temporal_frames)
    assert all(frame.source_width == 3840 and frame.source_height == 2160
               for frame in engine._temporal_frames)
    assert sum(frame.image.nbytes for frame in engine._temporal_frames) <= 3_000_000


def test_finalize_drops_incomplete_window_without_validation():
    class Validator:
        def validate_temporal(self, *args): raise AssertionError("must not validate partial window")
    engine = AbandonedObjectEngine("cam", [], {"abandoned_object": {
        "candidate_source": "static_regions", "owner_absent_seconds": 0,
        "temporal": {"enabled": True}}}, region_validator=Validator())
    region = StaticRegionObservation(region_id="pending", bbox=[0, 0, 5, 5],
        first_seen_at="2026-08-01T00:00:00Z", last_seen_at="2026-08-01T00:00:01Z",
        persistence_seconds=6, confidence=.8)
    for second in range(3):
        engine.submit_static_regions([region])
        engine.evaluate([], FrameData(camera_id="cam", frame_id=second + 1,
            captured_at=f"2026-08-01T00:00:0{second}Z", source_type="VIDEO",
            source_fps=1, inference_fps=1, image=np.zeros((10, 10, 3), dtype=np.uint8)))
    assert engine.finalize() == ["pending"]
    assert not engine._temporal_frames and "pending" not in engine.region_states
