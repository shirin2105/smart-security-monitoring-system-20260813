import unittest
from pathlib import Path

from kaggle_pipeline.phase8_kernel.phase8_kaggle_batch import (
    build_inference_template,
    materialize_code_bundle,
    unique_file,
)


class Phase8KaggleLauncherTests(unittest.TestCase):
    def test_code_bundle_materializes_support_files(self):
        import tempfile
        import zipfile

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_root = root / "input"
            input_root.mkdir()
            bundle = input_root / "phase8_code_bundle.zip"
            with zipfile.ZipFile(bundle, "w") as archive:
                archive.writestr("tools/phase8/phase8_batch_runner.py", "# runner")
            extracted = materialize_code_bundle(input_root, root / "working")
            self.assertEqual(unique_file("phase8_batch_runner.py", extracted).read_text(), "# runner")

    def test_kaggle_expanded_code_dataset_is_detected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temporary:
            dataset = Path(temporary) / "input" / "phase8-code"
            runner = dataset / "tools" / "phase8" / "phase8_batch_runner.py"
            runner.parent.mkdir(parents=True)
            runner.write_text("# runner")
            (dataset / "phase8_tracker_wrapper.py").write_text("# wrapper")
            self.assertEqual(materialize_code_bundle(Path(temporary) / "input"), dataset)

    def test_built_bundle_contains_phase7c_core(self):
        import subprocess
        import sys
        import tempfile
        import zipfile

        bundle = Path("kaggle_pipeline/phase8_code_dataset/phase8_code_bundle.zip")
        if not bundle.exists():
            self.skipTest("Phase 8 code bundle has not been built")
        with zipfile.ZipFile(bundle) as archive:
            names = {name.replace("\\", "/") for name in archive.namelist()}
        self.assertIn("kaggle_pipeline/phase7c_kernel/phase7c_core.py", names)
        with tempfile.TemporaryDirectory() as temporary:
            with zipfile.ZipFile(bundle) as archive:
                archive.extractall(temporary)
            code = (
                "import sys; sys.path.insert(0, sys.argv[1]); "
                "from app.cv.phase8_event_adapter import infer_abandoned_events; "
                "cfg={'abandoned': {'enabled': True, 'stationary_hold_s': 3, "
                "'owner_away_hold_s': 5}}; "
                "assert infer_abandoned_events([], 'clip', 'cam', cfg, 25.0) == []"
            )
            result = subprocess.run([sys.executable, "-c", code, temporary],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_outer_clip_format_preserves_nested_tracker_fields(self):
        tracker = "python tracker.py --video {video} --tracks {tracks} --work-dir {work_dir} --inference-profile {inference_profile}"
        template = build_inference_template(Path("inference_video.py"), tracker)
        command = template.format(video_path="clip.mp4", clip_id="clip-1", camera_id="cam",
                                  camera_config_path="cam.json", pred_path="pred.jsonl",
                                  clip_out_dir="out")
        self.assertIn("--clip-id clip-1", command)
        self.assertIn("{video}", command)
        self.assertIn("{inference_profile}", command)


if __name__ == "__main__":
    unittest.main()
