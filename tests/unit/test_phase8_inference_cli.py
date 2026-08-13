import tempfile
import unittest
from pathlib import Path

from tools.phase8.inference_video import _resolve_fps, load_tracks


class Phase8InferenceCliTests(unittest.TestCase):
    def test_empty_track_file_is_valid_negative_clip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tracks.jsonl"
            path.write_text("", encoding="utf-8")
            self.assertEqual(load_tracks(path), [])

    def test_track_row_requires_phase7c_center(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tracks.jsonl"
            path.write_text(
                '{"frame_index":0,"timestamp_s":0,"class_name":"luggage",'
                '"global_track_id":1,"bbox_xyxy":[0,0,1,1],"confidence":0.9}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "center_xy"):
                load_tracks(path)

    def test_fps_can_be_derived_from_track_timestamps(self):
        rows = [{"frame_index": 0, "timestamp_s": 0.0},
                {"frame_index": 25, "timestamp_s": 1.0}]
        self.assertEqual(_resolve_fps(Path("missing.mp4"), rows, None), 25.0)


if __name__ == "__main__":
    unittest.main()
