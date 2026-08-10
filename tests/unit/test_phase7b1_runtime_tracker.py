import importlib.util
from pathlib import Path
import sys
import types
import unittest

import numpy as np


CORE_PATH = (
    Path(__file__).parents[2]
    / "kaggle_pipeline"
    / "phase7b1_kernel"
    / "phase7b1_runtime_core.py"
)
SPEC = importlib.util.spec_from_file_location("phase7b1_runtime_core_for_test", CORE_PATH)
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
        self.local_id = len(self.instances) + 1
        self.instances.append(self)

    def reset(self):
        pass

    def update(self, detections, frame=None):
        return FakeDetections(
            detections.xyxy,
            detections.confidence,
            detections.class_id,
            np.full(len(detections.xyxy), self.local_id, dtype=int),
        )


class GenericLuggageTrackerTests(unittest.TestCase):
    def setUp(self):
        FakeByteTrackTracker.instances.clear()
        self.old_supervision = sys.modules.get("supervision")
        self.old_trackers = sys.modules.get("trackers")
        sys.modules["supervision"] = types.SimpleNamespace(Detections=FakeDetections)
        sys.modules["trackers"] = types.SimpleNamespace(ByteTrackTracker=FakeByteTrackTracker)

    def tearDown(self):
        for name, old in (("supervision", self.old_supervision), ("trackers", self.old_trackers)):
            if old is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old

    def test_exactly_two_class_isolated_trackers(self):
        tracker = CORE.RuntimeByteTrack(frame_rate=30.0)
        observations = tracker.update(
            [[0, 0, 10, 10], [20, 20, 30, 30]],
            [0.9, 0.8],
            [0, 1],
            frame_index=0,
            timestamp_s=0.0,
        )
        self.assertEqual(len(FakeByteTrackTracker.instances), 2)
        self.assertEqual([item.class_name for item in observations], ["person", "luggage"])
        self.assertEqual([item.global_track_id for item in observations], [1_000_001, 2_000_002])

    def test_candidate_is_suppressed_until_warmup_finishes(self):
        manager = CORE.CandidateManager(
            quality=CORE.QualityConfig(
                luggage_min_age_s=1.0,
                luggage_min_hits=2,
                luggage_min_high_hits=1,
            ),
            background=CORE.BackgroundConfig(
                warmup_s=8.0,
                min_duration_s=1.0,
                min_hits=3,
            ),
        )

        def observation(frame, timestamp):
            return CORE.TrackObservation(
                frame_index=frame,
                timestamp_s=timestamp,
                class_id=1,
                class_name="luggage",
                global_track_id=2_000_001,
                local_track_id=1,
                bbox_xyxy=(10.0, 10.0, 30.0, 30.0),
                confidence=0.8,
            )

        manager.process([observation(0, 0.0)], timestamp_s=0.0)
        before = manager.process([observation(30, 1.0)], timestamp_s=1.0)
        self.assertEqual(before[0]["status"], "TRACK_ONLY")
        self.assertFalse(before[0]["eligible"])

        after = manager.process([observation(240, 8.0)], timestamp_s=8.0)
        self.assertTrue(manager.warmup_finalized)
        self.assertEqual(after[0]["status"], "BACKGROUND")


if __name__ == "__main__":
    unittest.main()
