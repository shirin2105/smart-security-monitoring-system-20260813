import json
import unittest

from app.cv.phase7c_tracking import (
    StationaryFeatureConfig,
    StationaryFeatureExtractor,
    displacement_px,
    group_trajectories,
    load_track_jsonl,
    normalized_displacement,
)


def point_row(frame, timestamp, center, track_id=2_000_007):
    x, y = center
    return {
        "frame_index": frame,
        "timestamp_s": timestamp,
        "class_id": 1,
        "class_name": "backpack",
        "global_track_id": track_id,
        "local_track_id": 7,
        "bbox_xyxy": [x - 2, y - 2, x + 2, y + 2],
        "confidence": 0.8,
        "center_xy": [x, y],
    }


def load_points(tmp_path, rows):
    path = tmp_path / "tracks.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return list(load_track_jsonl(path))


class Phase7CTrackingFeatureTests(unittest.TestCase):
    def setUp(self):
        from tempfile import TemporaryDirectory

        self.temp_dir = TemporaryDirectory()
        from pathlib import Path

        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_displacement_and_normalization(self):
        points = load_points(
            self.temp_path,
            [point_row(0, 0.0, (0, 0)), point_row(1, 0.1, (3, 4))],
        )
        self.assertEqual(displacement_px(points), 5.0)
        self.assertEqual(normalized_displacement(points, 10.0), 0.5)

    def test_grouping_is_time_ordered(self):
        rows = [point_row(2, 0.2, (2, 0)), point_row(0, 0.0, (0, 0))]
        trajectory = group_trajectories(load_points(self.temp_path, rows))[2_000_007]
        self.assertEqual([point.frame_index for point in trajectory], [0, 2])

    def test_stationary_extractor_returns_features_without_decision(self):
        points = load_points(
            self.temp_path,
            [point_row(0, 0.0, (10, 10)), point_row(2, 0.2, (10, 10))],
        )
        state = StationaryFeatureExtractor(
            StationaryFeatureConfig(reference_size_px=100.0)
        ).extract(points)
        self.assertEqual(state.displacement_px, 0.0)
        self.assertEqual(state.displacement_normalized, 0.0)
        self.assertIsNone(state.stationary_score)
        self.assertIsNone(state.stationary_since)

    def test_stationary_thresholds_are_not_accepted(self):
        with self.assertRaisesRegex(ValueError, "outside this skeleton"):
            StationaryFeatureConfig(
                reference_size_px=100.0,
                stationary_displacement_threshold=0.1,
            )

    def test_jsonl_rejects_taxonomy_mismatch(self):
        row = point_row(0, 0.0, (0, 0))
        row["class_name"] = "person"
        with self.assertRaisesRegex(ValueError, "class_id/class_name mismatch"):
            load_points(self.temp_path, [row])


if __name__ == "__main__":
    unittest.main()
