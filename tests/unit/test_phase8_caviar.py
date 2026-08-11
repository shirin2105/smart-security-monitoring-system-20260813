from pathlib import Path
import unittest

from app.evaluation.phase8_caviar import camera_config, derive_events, parse_observations


class CaviarPhase8Tests(unittest.TestCase):
    def test_official_left_bag_xml_produces_abandoned_event(self):
        path = Path("phase8_dataset/source_xml/LeftBag.xml")
        if not path.exists():
            self.skipTest("CAVIAR source XML not downloaded")
        observations, _ = parse_observations(path)
        config = camera_config("CAM_LEFTBAG", "ABANDONED_OBJECT")
        events = derive_events("LeftBag", "CAM_LEFTBAG", observations, 25.0,
                               config["intrusion"]["roi_polygon"],
                               config["crowd"]["roi_polygon"])
        abandoned = [event for event in events if event["event_type"] == "ABANDONED_OBJECT"]
        self.assertEqual(len(abandoned), 1)
        self.assertIn("role='leaving object'", abandoned[0]["notes"])

    def test_non_target_control_rois_do_not_invent_events(self):
        path = Path("phase8_dataset/source_xml/Browse1.xml")
        if not path.exists():
            self.skipTest("CAVIAR source XML not downloaded")
        observations, _ = parse_observations(path)
        config = camera_config("CAM_BROWSE1", "MIXED_NEGATIVE")
        events = derive_events("Browse1", "CAM_BROWSE1", observations, 25.0,
                               config["intrusion"]["roi_polygon"],
                               config["crowd"]["roi_polygon"])
        self.assertEqual(events, [])

    def test_behind_chair_manual_event_is_disclosed(self):
        path = Path("phase8_dataset/source_xml/LeftBag_BehindChair.xml")
        if not path.exists():
            self.skipTest("CAVIAR source XML not downloaded")
        observations, _ = parse_observations(path)
        config = camera_config("CAM_TEST", "ABANDONED_OBJECT")
        events = derive_events("LeftBag_BehindChair", "CAM_TEST", observations, 25.0,
                               config["intrusion"]["roi_polygon"],
                               config["crowd"]["roi_polygon"])
        abandoned = [event for event in events if event["event_type"] == "ABANDONED_OBJECT"]
        self.assertEqual(len(abandoned), 1)
        self.assertIn("Manual video review", abandoned[0]["notes"])


if __name__ == "__main__":
    unittest.main()
