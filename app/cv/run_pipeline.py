"""Chạy CV pipeline: đọc clip từ cameras.yaml, detect + event engine, publish EventCandidate.

Publish tới back-end API qua HttpEventPublisher (mặc định http://127.0.0.1:8000/api/v1/events/ingest).
Cấu hình endpoint qua env EVENT_INGEST_URL.

Usage:
    .venv/Scripts/python.exe -m app.cv.run_pipeline [--max-frames N] [--camera cam_01]
"""

from __future__ import annotations

import argparse
import sys

from app.config import settings
from app.cv.multi_camera_runner import MultiCameraRunner


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CV event detection pipeline")
    parser.add_argument("--max-frames", type=int, default=None, help="Cap frames per camera")
    parser.add_argument("--camera", type=str, default=None, help="Run single camera (camera_id)")
    args = parser.parse_args()

    configs = settings.cameras
    if args.camera:
        configs = [c for c in configs if c["camera_id"] == args.camera]
        if not configs:
            print(f"No camera config for {args.camera}", file=sys.stderr)
            return 1

    print(f"Running CV pipeline: {len(configs)} camera(s), ingest -> {settings.event_ingest_url}")
    runner = MultiCameraRunner(camera_configs=configs)
    results = runner.run(max_frames=args.max_frames)

    total = 0
    for camera_id, res in results.items():
        status = res["status"]
        n = len(res.get("events", []))
        total += n
        print(f"  {camera_id}: {status} ({n} events)")
    print(f"Total EventCandidates published: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
