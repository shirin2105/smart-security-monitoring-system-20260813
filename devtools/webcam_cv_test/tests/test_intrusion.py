import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from webcam_event_adapter import RealtimeEventAdapter


def person(track_id, x1, x2):
    return {"class_name": "person", "eligible": True, "global_track_id": track_id,
            "bbox_xyxy": [x1, 10, x2, 100], "frame_index": 0, "timestamp_s": 0,
            "center_xy": [(x1+x2)/2, 55], "confidence": .9}


class IntrusionTests(unittest.TestCase):
    def test_active_clear_and_reentry_use_bottom_center(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = {"camera_id":"C", "intrusion":{"enabled":True,"hold_s":1},
                      "crowd":{"enabled":False}, "abandoned":{"enabled":False}}
            adapter = RealtimeEventAdapter(config, Path(temporary)/"events.jsonl",
                                            Path(__file__).resolve().parents[3])
            self.assertEqual(adapter.update([person(1, 60, 80)], 0.0, 100), [])
            self.assertEqual(adapter.update([person(1, 60, 80)], 1.1, 100)[0]["state"], "ACTIVE")
            self.assertEqual(adapter.update([person(1, 60, 80)], 1.2, 100), [])
            self.assertEqual(adapter.update([person(1, 10, 30)], 1.3, 100)[0]["state"], "CLEARED")
            self.assertEqual(adapter.update([person(1, 60, 80)], 2.0, 100), [])
            self.assertEqual(adapter.update([person(1, 60, 80)], 3.1, 100)[0]["state"], "ACTIVE")


if __name__ == "__main__": unittest.main()
