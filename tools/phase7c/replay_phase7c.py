from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from app.cv.phase7c_tracking.event_contract import AbandonedObjectCandidate


REPO_ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = REPO_ROOT / "kaggle_pipeline" / "phase7c_kernel"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from phase7c_core import (  # noqa: E402
    OwnerConfig,
    Phase7CConfig,
    QualityConfig,
    StationaryConfig,
    StitchConfig,
    annotate_video,
    infer_phase7c,
    load_jsonl,
)


def _load_camera_config(path: Path | None, camera_id: str | None) -> dict[str, Any]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    cameras = payload.get("cameras")
    if not isinstance(cameras, dict) or not camera_id:
        raise ValueError("--camera-id is required with a camera config")
    if camera_id not in cameras:
        raise ValueError(f"camera config not found: {camera_id}")
    config = cameras[camera_id]
    if not isinstance(config, dict):
        raise ValueError("camera config must be an object")
    return config


def _build_config(data: dict[str, Any]) -> Phase7CConfig:
    return Phase7CConfig(
        quality=QualityConfig(**data.get("quality", {})),
        stitch=StitchConfig(**data.get("stitch", {})),
        stationary=StationaryConfig(**data.get("stationary", {})),
        owner=OwnerConfig(**data.get("owner", {})),
        roi_polygon=data.get("roi_polygon"),
    )


def _write_outputs(output_dir: Path, result: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "phase7c_summary.json": result["summary"],
        "quality_report.json": result["quality_report"],
        "physical_luggage.json": result["physical_luggage"],
        "owner_associations.json": result["owner_associations"],
        "phase7c_events.json": result["events"],
    }
    for name, payload in payloads.items():
        (output_dir / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    with (output_dir / "phase7c_timeline.jsonl").open("w", encoding="utf-8") as handle:
        for row in result["timeline"]:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def run(args: argparse.Namespace) -> dict[str, Any]:
    config_data = _load_camera_config(args.config, args.camera_id)
    config = _build_config(config_data)
    rows = load_jsonl(args.tracks)
    result = infer_phase7c(rows, config, fps_hint=args.fps)
    result["events"] = [
        AbandonedObjectCandidate.from_mapping(event).to_dict()
        for event in result["events"]
    ]
    _write_outputs(args.output_dir, result)
    if args.video:
        annotate_video(
            args.video,
            rows,
            result,
            args.output_dir / "annotated_phase7c.mp4",
        )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay Phase 7C from Phase 7B.1 tracks")
    parser.add_argument("--tracks", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--video", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--camera-id")
    parser.add_argument("--fps", type=float, default=29.97)
    return parser.parse_args()


if __name__ == "__main__":
    replay = run(parse_args())
    print(json.dumps(replay["summary"], indent=2))
