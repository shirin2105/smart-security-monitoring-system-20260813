"""Run configured cameras through unified CV and local CVEvent v1 JSONL output.

Usage:
    .venv/Scripts/python.exe -m app.cv.run_pipeline [--max-frames N] [--camera cam_01]
"""

from __future__ import annotations

import argparse
import sys

from app.config import settings
from app.cv.multi_camera_runner import MultiCameraRunner


def main() -> int:
    parser = argparse.ArgumentParser(description="Run unified CV event pipeline")
    parser.add_argument("--max-frames", type=int, default=None, help="Cap frames per camera")
    parser.add_argument("--camera", type=str, default=None, help="Run one configured camera")
    parser.add_argument("--no-loop", action="store_true", help="Do not loop video clips")
    parser.add_argument("--fast", "--no-realtime", action="store_true", help="Run without real-time pacing")
    args = parser.parse_args()

    configs = settings.cameras
    if args.camera:
        configs = [config for config in configs if config["camera_id"] == args.camera]
        if not configs:
            print(f"No camera config for {args.camera}", file=sys.stderr)
            return 1

    realtime = not args.fast
    print(f"Running CV pipeline: {len(configs)} camera(s), local CVEvent v1 JSONL")
    results = MultiCameraRunner(
        camera_configs=configs, loop=not args.no_loop, realtime=realtime
    ).run(max_frames=args.max_frames)
    total = 0
    for camera_id, result in results.items():
        status = result["status"]
        count = len(result.get("events", []))
        total += count
        print(f"  {camera_id}: {status} ({count} events)")
    print(f"Total CVEvents published: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
