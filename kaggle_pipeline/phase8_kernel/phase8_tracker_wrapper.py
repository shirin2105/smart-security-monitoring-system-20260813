from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Invoke the frozen Phase 7B.1 tracker for one clip")
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--tracks", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--inference-profile", choices=("full640", "tile768_overlap20"), required=True)
    args = parser.parse_args()
    runner_path = Path(__file__).with_name("phase7b1_kaggle_v4_generic_luggage.py")
    spec = importlib.util.spec_from_file_location("phase7b1_frozen", runner_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import frozen tracker: {runner_path}")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    args.work_dir.mkdir(parents=True, exist_ok=True)
    module.OUT = args.work_dir / "phase7b1_generic_luggage"
    module.MAX_SECONDS = 0.0
    module.MODE = args.inference_profile
    os.environ["VIDEO_PATH"] = str(args.video)
    module.main()
    source = module.OUT / "tracks_v4.jsonl"
    if not source.is_file():
        raise FileNotFoundError(source)
    args.tracks.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, args.tracks)


if __name__ == "__main__":
    main()
