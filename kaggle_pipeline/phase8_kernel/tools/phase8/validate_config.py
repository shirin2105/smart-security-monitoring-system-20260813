from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.evaluation.phase8_config import load_json, validate_camera_config, validate_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Phase 8 manifest and camera configs")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--allow-small-manifest", action="store_true")
    args = parser.parse_args()
    clips = validate_manifest(load_json(args.manifest), not args.allow_small_manifest)
    for clip in clips:
        path = Path(clip["camera_config_path"])
        if not path.is_absolute():
            path = (args.manifest.parent / path).resolve()
        validate_camera_config(load_json(path), str(clip["camera_id"]))
    print(f"PHASE8 CONFIG VALID: clips={len(clips)}")


if __name__ == "__main__":
    main()
