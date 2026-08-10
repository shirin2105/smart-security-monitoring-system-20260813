import unittest

from app.cv.phase8_event_adapter import infer_rule_events


class Phase8RuleAdapterTests(unittest.TestCase):
    def test_intrusion_and_crowd_share_prediction_schema(self):
        config = {
            "intrusion": {"enabled": True, "roi_polygon": [[0, 0], [100, 0], [100, 100], [0, 100]],
                          "hold_s": 0},
            "crowd": {"enabled": True, "roi_polygon": [[0, 0], [100, 0], [100, 100], [0, 100]],
                      "threshold": 2, "hold_s": 0, "release_threshold": 1},
        }
        rows = []
        for frame_index, timestamp in enumerate((0.0, 0.1, 0.2)):
            for track_id, x in ((1, 10), (2, 40)):
                rows.append({"frame_index": frame_index, "timestamp_s": timestamp,
                             "class_name": "person", "global_track_id": track_id,
                             "bbox_xyxy": [x, 10, x + 10, 30], "confidence": 0.9})
        events = infer_rule_events(rows, "clip", "cam", config, 10.0)
        self.assertEqual({event.event_type for event in events},
                         {"ZONE_INTRUSION", "CROWD_THRESHOLD"})
        self.assertTrue(all(event.clip_id == "clip" for event in events))

    def test_empty_frames_reset_pending_crowd(self):
        config = {
            "intrusion": {"enabled": False},
            "crowd": {"enabled": True, "roi_polygon": [[0, 0], [100, 0], [100, 100], [0, 100]],
                      "threshold": 2, "hold_s": 3, "release_threshold": 1},
        }
        rows = []
        for frame_index in (0, 100):
            for track_id in (1, 2):
                rows.append({"frame_index": frame_index, "timestamp_s": float(frame_index),
                             "class_name": "person", "global_track_id": track_id,
                             "bbox_xyxy": [10, 10, 20, 30], "confidence": 0.9})
        events = infer_rule_events(rows, "clip", "cam", config, 1.0)
        self.assertFalse(any(event.event_type == "CROWD_THRESHOLD" for event in events))


if __name__ == "__main__":
    unittest.main()
