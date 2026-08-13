from types import SimpleNamespace

import numpy as np
import pytest

from app.common.schemas import DetectionResult, FrameData
from app.cv.tracker import ByteTrackMultiObjectTracker


def frame(timestamp="2026-01-01T00:00:00Z"):
    return FrameData(camera_id="cam", frame_id=1, captured_at=timestamp,
                     source_type="SIMULATED", source_fps=25, inference_fps=5)


class FakeTracker:
    def __init__(self, returned_id):
        self.returned_id = returned_id
        self.calls = []
    def update(self, detections, frame=None):
        self.calls.append((detections, frame))
        if len(detections[0]) == 0:
            return SimpleNamespace(tracker_id=None)
        return SimpleNamespace(xyxy=detections[0], confidence=detections[1],
                               class_id=detections[2], tracker_id=np.array([self.returned_id]))


def test_two_class_trackers_update_every_frame_and_namespace_ids():
    created = []
    def factory(*args, **kwargs):
        tracker = FakeTracker(7); created.append(tracker); return tracker
    make = lambda x, s, c: (x, s, c)
    tracker = ByteTrackMultiObjectTracker("cam", tracker_factory=factory, detections_factory=make)
    detections = [DetectionResult(class_id=0, class_name="person", bbox=[0, 0, 10, 10], confidence=.8),
                  DetectionResult(class_id=1, class_name="luggage", bbox=[20, 20, 30, 30], confidence=.7)]
    results = tracker.track(detections, frame())
    assert len(created) == 2 and all(len(item.calls) == 1 for item in created)
    assert results[1].track_id - results[0].track_id == 100_000
    assert all(item.calls[0][1] is None for item in created)
    assert all(item.first_seen_at == "2026-01-01T00:00:00Z" for item in results)
    assert all(item.last_seen_at == "2026-01-01T00:00:00Z" for item in results)
    other = ByteTrackMultiObjectTracker("other", tracker_factory=factory, detections_factory=make)
    assert other.track(detections[:1], frame())[0].track_id != results[0].track_id


def test_empty_frame_ages_both_trackers():
    created = []
    def factory(*args, **kwargs):
        tracker = FakeTracker(1); created.append(tracker); return tracker
    tracker = ByteTrackMultiObjectTracker("cam", tracker_factory=factory,
                                          detections_factory=lambda x, s, c: (x, s, c))
    assert tracker.track([], frame()) == []
    assert all(len(item.calls) == 1 for item in created)


def test_invalid_detection_rejected():
    tracker = ByteTrackMultiObjectTracker("cam", tracker_factory=lambda *a, **k: FakeTracker(1),
                                          detections_factory=lambda x, s, c: (x, s, c))
    bad = DetectionResult(class_id=0, class_name="person", bbox=[2, 0, 1, 2], confidence=.8)
    with pytest.raises(ValueError, match="ordered"):
        tracker.track([bad], frame())


def test_first_seen_expires_only_after_lost_track_buffer_and_id_reuse_resets():
    tracker = ByteTrackMultiObjectTracker(
        "cam", lost_track_buffer=2,
        tracker_factory=lambda *a, **k: FakeTracker(4),
        detections_factory=lambda x, s, c: (x, s, c),
    )
    detection = DetectionResult(class_id=0, class_name="person", bbox=[0, 0, 10, 10], confidence=.8)
    first = tracker.track([detection], frame("t0"))[0]
    tracker.track([], frame("t1"))
    tracker.track([], frame("t2"))
    assert first.track_id in tracker._first_seen
    tracker.track([], frame("t3"))
    assert first.track_id not in tracker._first_seen
    reused = tracker.track([detection], frame("t4"))[0]
    assert reused.track_id == first.track_id
    assert reused.first_seen_at == "t4"
