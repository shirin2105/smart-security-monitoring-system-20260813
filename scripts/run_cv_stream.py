#!/usr/bin/env python3
"""Run real-time CV streaming pipeline and send events + telemetry to backend."""

import argparse
import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import settings
from app.cv.multi_camera_runner import MultiCameraRunner
from app.publisher.http_publisher import HttpEventPublisher


def main():
    parser = argparse.ArgumentParser(description="Run CV Streaming with real-time telemetry")
    parser.add_argument("--clip", default="tests/clips/walking_people.mp4", help="Path to video clip")
    parser.add_argument("--camera-id", default="cam_01", help="Camera ID (e.g. cam_01, cam_02)")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000/api/v1/events/ingest", help="Backend ingest endpoint")
    parser.add_argument("--token", default=os.getenv("EVENT_INGEST_TOKEN", "mock-token-change-in-production"), help="Bearer token")
    parser.add_argument("--fps", type=float, default=5.0, help="Inference FPS")
    parser.add_argument("--frames", type=int, default=None, help="Max frames per cycle (None for infinite loop)")
    parser.add_argument("--all-cameras", action="store_true", help="Run all enabled cameras in config")
    args = parser.parse_args()

    clip_path = args.clip if os.path.isabs(args.clip) else str(ROOT_DIR / args.clip)
    if not args.all_cameras and not os.path.exists(clip_path):
        print(f"[ERROR] Clip not found: {clip_path}")
        sys.exit(1)

    publisher = HttpEventPublisher(
        endpoint_url=args.api_url,
        bearer_token=args.token,
        timeout_seconds=2.0,
    )

    if args.all_cameras:
        camera_configs = settings.cameras
    else:
        camera_configs = [
            {
                "camera_id": args.camera_id,
                "source_uri": clip_path,
                "source_type": "SIMULATED",
                "inference_fps": args.fps,
                "enabled": True,
            }
        ]

    print("==================================================")
    print("🚀 Starting Real-Time CV Stream Pipeline")
    print(f"📡 Backend URL : {args.api_url}")
    print(f"📹 Cameras     : {[c['camera_id'] for c in camera_configs]}")
    print(f"⏱️  FPS         : {args.fps}")
    print("==================================================")

    runner = MultiCameraRunner(
        camera_configs=camera_configs,
        publisher=publisher,
        loop=True,
        realtime=True,
    )

    try:
        while True:
            res = runner.run(max_frames=args.frames)
            for cam, status in res.items():
                event_count = len(status.get("events", []))
                print(f"[{time.strftime('%H:%M:%S')}] {cam}: {status['status']} ({event_count} events generated)")
            if args.frames is not None:
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopped CV Stream.")


if __name__ == "__main__":
    main()
