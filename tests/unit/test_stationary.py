import json
from pathlib import Path
import tempfile
import unittest

from app.cv.phase7c_tracking.stationary import extract_stationary_features
from app.cv.phase7c_tracking.trajectory_loader import load_trajectories


class StationaryFeatureTests(unittest.TestCase):
    def test_generic_luggage_jsonl_and_displacement(self):
        rows = []
        for frame, center in ((0, (10.0, 10.0)), (1, (13.0, 14.0))):
            x, y = center
            rows.append({
                "frame_index": frame,
                "timestamp_s": frame / 10,
                "class_id": 1,
                "class_name": "luggage",
                "global_track_id": 2_000_001,
                "local_track_id": 1,
                "bbox_xyxy": [x - 2, y - 2, x + 2, y + 2],
                "confidence": 0.8,
                "center_xy": [x, y],
            })
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tracks_v4.jsonl"
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            trajectory = load_trajectories(path)[2_000_001]
        state = extract_stationary_features(trajectory, reference_size_px=10.0)
        self.assertEqual(state.luggage_track_id, 2_000_001)
        self.assertEqual(state.displacement_normalized, 0.5)
        self.assertIsNone(state.stationary_score)
        self.assertIsNone(state.stationary_since)

    def test_person_is_rejected(self):
        from app.cv.phase7c_tracking.jsonl_loader import TrackPoint

        point = TrackPoint(0, 0.0, 0, "person", 1_000_001, 1, (0, 0, 1, 1), 0.9, (0.5, 0.5))
        with self.assertRaisesRegex(ValueError, "luggage trajectory"):
            extract_stationary_features([point], reference_size_px=10.0)


if __name__ == "__main__":
    unittest.main()
