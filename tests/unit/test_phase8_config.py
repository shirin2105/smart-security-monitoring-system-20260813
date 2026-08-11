import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.evaluation.phase8_config import load_json, validate_camera_config, validate_manifest


CAMERA = {
    "camera_id": "CAM_01",
    "inference_profile": "full640",
    "intrusion": {"enabled": True, "roi_polygon": [[0, 0], [10, 0], [10, 10]], "hold_s": 1},
    "crowd": {"enabled": True, "roi_polygon": [[0, 0], [10, 0], [10, 10]],
              "threshold": 2, "hold_s": 1},
    "abandoned": {"enabled": True, "valid_floor_roi_polygon": [[0, 0], [10, 0], [10, 10]],
                  "stationary_hold_s": 3, "owner_away_hold_s": 5},
}


class Phase8ConfigTests(unittest.TestCase):
    def test_load_json_accepts_utf8_bom(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.json"
            path.write_bytes(b"\xef\xbb\xbf{\"clips\": []}")
            self.assertEqual(load_json(path), {"clips": []})

    def test_camera_config_valid(self):
        self.assertEqual(validate_camera_config(CAMERA, "CAM_01"), CAMERA)

    def test_manifest_requires_twenty_clips(self):
        with self.assertRaisesRegex(ValueError, "20-30"):
            validate_manifest({"clips": []})

    def test_smoke_manifest_still_requires_positive_and_negative(self):
        clips = [
            {"clip_id": "p", "video_path": "p.mp4", "camera_id": "c",
             "camera_config_path": "c.json", "scenario_tags": ["positive"],
             "expected_duration_s": 1},
            {"clip_id": "n", "video_path": "n.mp4", "camera_id": "c",
             "camera_config_path": "c.json", "scenario_tags": ["negative"],
             "expected_duration_s": 1},
        ]
        self.assertEqual(len(validate_manifest({"clips": clips}, False)), 2)

    def test_disabled_sections_do_not_require_thresholds_or_polygons(self):
        config = {"camera_id": "CAM_01", "inference_profile": "full640",
                  "intrusion": {"enabled": False}, "crowd": {"enabled": False},
                  "abandoned": {"enabled": False}}
        self.assertEqual(validate_camera_config(config, "CAM_01"), config)

    def test_production_manifest_requires_each_event_positive_and_negative(self):
        clips = []
        for index in range(20):
            clips.append({"clip_id": str(index), "video_path": "x.mp4", "camera_id": "c",
                          "camera_config_path": "c.json",
                          "scenario_tags": ["abandoned_positive" if index % 2 else "abandoned_negative"],
                          "expected_duration_s": 1})
        with self.assertRaisesRegex(ValueError, "ZONE_INTRUSION"):
            validate_manifest({"clips": clips})


if __name__ == "__main__":
    unittest.main()
