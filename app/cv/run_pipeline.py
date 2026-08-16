"""Run configured cameras through unified CV and local CVEvent v1 JSONL output.

Usage:
    .venv/Scripts/python.exe -m app.cv.run_pipeline [--max-frames N] [--camera cam_01] [--http]
"""

from __future__ import annotations

import argparse
import os
import sys

from app.config import settings
from app.cv.multi_camera_runner import MultiCameraRunner
from app.publisher.composite_publisher import CompositePublisher
from app.publisher.http_publisher import HttpEventPublisher
from app.publisher.jsonl_publisher import JsonlPublisher


def main() -> int:
    parser = argparse.ArgumentParser(description="Run unified CV event pipeline")
    parser.add_argument("--max-frames", type=int, default=None, help="Cap frames per camera")
    parser.add_argument("--camera", type=str, default=None, help="Run one configured camera")
    parser.add_argument("--no-loop", action="store_true", help="Do not loop video clips")
    parser.add_argument("--fast", "--no-realtime", action="store_true", help="Run without real-time pacing")
    parser.add_argument(
        "--http", "--stream",
        dest="stream_http",
        action="store_true",
        help="Stream realtime telemetry and events to backend via HTTP",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default=os.getenv("EVENT_INGEST_URL", "http://127.0.0.1:8000/api/v1/events/ingest"),
        help="Backend ingest endpoint URL (default: $EVENT_INGEST_URL or http://127.0.0.1:8000/api/v1/events/ingest)",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=os.getenv("EVENT_INGEST_TOKEN", "dummy"),
        help="Backend ingest auth bearer token (default: $EVENT_INGEST_TOKEN or dummy)",
    )
    args = parser.parse_args()

    configs = settings.cameras
    if args.camera:
        configs = [config for config in configs if config["camera_id"] == args.camera]
        if not configs:
            print(f"No camera config for {args.camera}", file=sys.stderr)
            return 1

    realtime = not args.fast
    should_stream = args.stream_http or bool(os.getenv("EVENT_INGEST_URL"))

    jsonl_publisher = JsonlPublisher(output_path=settings.artifact_dir / "events" / "cv-events.jsonl")
    if should_stream:
        http_publisher = HttpEventPublisher(
            endpoint_url=args.api_url,
            bearer_token=args.token,
        )
        publisher = CompositePublisher([jsonl_publisher, http_publisher])
        print(f"Running CV pipeline: {len(configs)} camera(s), local CVEvent v1 JSONL + HTTP streaming ({args.api_url})")
    else:
        publisher = jsonl_publisher
        print(f"Running CV pipeline: {len(configs)} camera(s), local CVEvent v1 JSONL")

    results = MultiCameraRunner(
        camera_configs=configs,
        loop=not args.no_loop,
        realtime=realtime,
        publisher=publisher,
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
