from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cv.phase8_event_adapter import infer_all_events
from app.evaluation.phase8_config import load_json, validate_camera_config


def load_tracks(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.strip():
                row = json.loads(line)
                missing = {"frame_index", "timestamp_s", "class_name", "global_track_id",
                           "bbox_xyxy", "center_xy", "confidence"} - set(row)
                if missing:
                    raise ValueError(f"track row {line_number} missing {sorted(missing)}")
                rows.append(row)
    return rows


def materialize_tracks(args: argparse.Namespace, config: dict) -> Path:
    if args.tracks:
        if not args.tracks.is_file():
            raise FileNotFoundError(args.tracks)
        return args.tracks
    template = args.tracker_cmd_template or os.environ.get("PHASE8_TRACKER_CMD")
    if not template:
        raise ValueError("provide --tracks or --tracker-cmd-template/PHASE8_TRACKER_CMD")
    tracks_path = args.work_dir / "tracks_v4.jsonl"
    fields = {"video": str(args.video), "tracks": str(tracks_path),
              "work_dir": str(args.work_dir), "camera_id": args.camera_id,
              "inference_profile": config["inference_profile"]}
    command = shlex.split(template.format(**fields))
    print("[TRACKER]", shlex.join(command), flush=True)
    subprocess.run(command, check=True)
    if not tracks_path.is_file():
        raise FileNotFoundError(f"tracker did not create {tracks_path}")
    return tracks_path


def _resolve_fps(video: Path, rows: list[dict], hint: float | None) -> float:
    if hint is not None:
        if hint <= 0:
            raise ValueError("--fps-hint must be positive")
        return hint
    try:
        import cv2
        capture = cv2.VideoCapture(str(video))
        fps = float(capture.get(cv2.CAP_PROP_FPS)) if capture.isOpened() else 0.0
        capture.release()
        if fps > 0:
            return fps
    except ImportError:
        pass
    estimates = []
    for left, right in zip(rows, rows[1:]):
        frame_delta = int(right["frame_index"]) - int(left["frame_index"])
        time_delta = float(right["timestamp_s"]) - float(left["timestamp_s"])
        if frame_delta > 0 and time_delta > 0:
            estimates.append(frame_delta / time_delta)
    if estimates:
        return sorted(estimates)[len(estimates) // 2]
    raise ValueError("could not determine video FPS; provide --fps-hint")


def _resolve_duration(video: Path, rows: list[dict], fps: float) -> float:
    try:
        import cv2
        capture = cv2.VideoCapture(str(video))
        frames = float(capture.get(cv2.CAP_PROP_FRAME_COUNT)) if capture.isOpened() else 0.0
        capture.release()
        if frames > 0:
            return frames / fps
    except ImportError:
        pass
    if rows:
        return max(float(row["timestamp_s"]) for row in rows) + 1.0 / fps
    raise ValueError("could not determine processed video duration")


def run(args: argparse.Namespace) -> list[dict]:
    if not args.video.is_file():
        raise FileNotFoundError(args.video)
    args.work_dir.mkdir(parents=True, exist_ok=True)
    config = validate_camera_config(load_json(args.camera_config), args.camera_id)
    rows = load_tracks(materialize_tracks(args, config))
    fps = _resolve_fps(args.video, rows, args.fps_hint)
    duration_s = _resolve_duration(args.video, rows, fps)
    events = infer_all_events(rows, args.clip_id or args.video.stem, args.camera_id,
                              config, fps)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
    (args.work_dir / "phase8_runtime_summary.json").write_text(json.dumps({
        "clip_id": args.clip_id or args.video.stem,
        "processed_duration_s": duration_s,
        "source_fps": fps,
        "inference_profile": config["inference_profile"],
        "event_count": len(events),
    }, indent=2), encoding="utf-8")
    print(f"[PHASE8] events={len(events)} output={args.out}")
    return [event.to_dict() for event in events]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Thin Phase 8 adapter over frozen tracking/events")
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--camera-id", required=True)
    parser.add_argument("--camera-config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--clip-id")
    parser.add_argument("--tracks", type=Path)
    parser.add_argument("--tracker-cmd-template")
    parser.add_argument("--work-dir", type=Path, default=Path("artifacts/phase8-inference"))
    parser.add_argument("--fps-hint", type=float)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
