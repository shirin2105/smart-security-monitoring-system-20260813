import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from tools.phase8.phase8_batch_runner import run


class Phase8BatchRunnerTests(unittest.TestCase):
    def test_continue_on_error_still_fails_final_batch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            failing = root / "fail.py"
            failing.write_text("raise SystemExit(7)\n", encoding="utf-8")
            clips = []
            for clip_id, tag in (("positive", "intrusion_positive"),
                                 ("negative", "intrusion_negative")):
                clips.append({"clip_id": clip_id, "video_path": "missing.mp4",
                              "camera_id": "cam", "camera_config_path": "missing.json",
                              "scenario_tags": [tag], "expected_duration_s": 1})
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"clips": clips}), encoding="utf-8")
            args = Namespace(manifest=manifest, out_root=root / "out",
                             infer_cmd_template=f'"{sys.executable}" "{failing}"',
                             continue_on_error=True, allow_small_manifest=True)
            with self.assertRaisesRegex(RuntimeError, "2/2 clips"):
                run(args)
            status = json.loads((root / "out" / "batch_status.json").read_text(encoding="utf-8"))
            self.assertTrue(all(not row["ok"] for row in status))


if __name__ == "__main__":
    unittest.main()
