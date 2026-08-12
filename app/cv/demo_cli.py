from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import httpx
import websockets

from app.cv.demo_flow import DemoFailure, load_config, preflight, run_demo


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify MP4 -> CV -> incident -> NEW_ALERT")
    parser.add_argument("--config", default="configs/cv-web-demo.yaml")
    args = parser.parse_args()
    try:
        config = load_config(Path(args.config))
        preflight(config)
        result = asyncio.run(run_demo(config))
        print(f"PASS candidate={result['candidate_id']} incident={result['incident']['id']}")
        return 0
    except (DemoFailure, KeyError, TimeoutError, OSError, httpx.HTTPError, websockets.WebSocketException) as exc:
        print(f"DEMO FAILED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
