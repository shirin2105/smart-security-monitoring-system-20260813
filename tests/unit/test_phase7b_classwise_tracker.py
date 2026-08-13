import importlib.util
from pathlib import Path
import sys
import types
import unittest

import numpy as np


CORE_PATH = (
    Path(__file__).parents[2]
    / "kaggle_pipeline"
    / "phase7b_kernel"
    / "phase7b_core.py"
)
SPEC = importlib.util.spec_from_file_location("phase7b_core_for_test", CORE_PATH)
CORE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CORE
SPEC.loader.exec_module(CORE)


class FakeDetections:
    def __init__(self, xyxy, confidence, class_id, tracker_id=None):
        self.xyxy = np.asarray(xyxy)
        self.confidence = np.asarray(confidence)
        self.class_id = np.asarray(class_id)
        self.tracker_id = tracker_id

    @classmethod
    def empty(cls):
        return cls(np.empty((0, 4)), np.empty(0), np.empty(0, dtype=int))


class FakeByteTrackTracker:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.local_id = len(self.instances) + 1
        self.instances.append(self)

    def reset(self):
        pass

    def update(self, detections, frame=None):
        count = len(detections.xyxy)
        ids = np.full(count, self.local_id, dtype=int)
        return FakeDetections(
            detections.xyxy,
            detections.confidence,
            detections.class_id,
            tracker_id=ids,
        )


class ClasswiseByteTrackTests(unittest.TestCase):
    def setUp(self):
        FakeByteTrackTracker.instances.clear()
        self.previous_supervision = sys.modules.get("supervision")
        self.previous_trackers = sys.modules.get("trackers")
        sys.modules["supervision"] = types.SimpleNamespace(Detections=FakeDetections)
        sys.modules["trackers"] = types.SimpleNamespace(ByteTrackTracker=FakeByteTrackTracker)

    def tearDown(self):
        for name, previous in (
            ("supervision", self.previous_supervision),
            ("trackers", self.previous_trackers),
        ):
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous

    def test_uses_one_tracker_per_class_and_namespaces_ids(self):
        tracker = CORE.ClasswiseByteTrack(frame_rate=30.0)
        observations = tracker.update(
            xyxy=[[0, 0, 10, 10], [20, 20, 30, 30]],
            confidence=[0.9, 0.8],
            class_id=[0, 3],
            frame_index=0,
            timestamp_s=0.0,
        )
        self.assertEqual(len(FakeByteTrackTracker.instances), 4)
        self.assertEqual([item.class_id for item in observations], [0, 3])
        self.assertEqual(
            [item.global_track_id for item in observations],
            [1_000_001, 4_000_004],
        )

    def test_drops_unknown_and_below_threshold_detections(self):
        tracker = CORE.ClasswiseByteTrack(frame_rate=30.0)
        observations = tracker.update(
            xyxy=[[0, 0, 1, 1], [1, 1, 2, 2]],
            confidence=[0.01, 0.9],
            class_id=[0, 9],
            frame_index=0,
            timestamp_s=0.0,
        )
        self.assertEqual(observations, [])


if __name__ == "__main__":
    unittest.main()
