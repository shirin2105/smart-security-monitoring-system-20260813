"""Phase 11 real inference: run the unified CV worker over CAVIAR clips.

Runs under the deimv2 venv (torch/CUDA). Produces canonical cv-event-v1 records
in ``artifacts/phase11/predictions_all.jsonl`` (one line per lifecycle record).

Usage:
    third_party\\deimv2\\.python311\\python.exe scripts/phase11_infer.py
"""

from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.cv.detector import DEIMv2Detector
from app.cv.worker import CVWorker

CLIP_DIR = Path("phase8_dataset/videos")
CENTRAL_ROI = [[115, 115], [269, 115], [269, 259], [115, 259]]  # central region of 384x288
INFERENCE_FPS = 5.0

CROWD_RULES = {
    "count_threshold": 3,
    "hold_seconds": 4.0,
    "release_threshold": 2,
    "cooldown_seconds": 30,
}

INTRUSION_RULES = {
    "dwell_seconds": 2.0,
    "exit_grace_seconds": 1.0,
    "cooldown_seconds": 30,
}


class CollectingPublisher:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def publish(self, event) -> bool:
        self.events.append(event.to_dict())
        return True


def build_rules() -> dict:
    rules = {"intrusion": INTRUSION_RULES, "crowd": CROWD_RULES, "abandoned_object": {}}
    rules["abandoned_object"] = {"phase7c": _phase7c_config()}
    return rules


def _phase7c_config() -> dict:
    base = dict(settings.load_yaml("event_rules.yaml").get("abandoned_object", {}).get("phase7c", {}))
    # Product Policy v2: ABANDONED_OBJECT is full-frame. The valid-floor ROI is no
    # longer applied (the adapter ignores it), so it is dropped from the run config.
    base.pop("valid_floor_roi_polygon", None)
    if os.getenv("PHASE11B_TRACE") == "1":
        base["debug"] = {
            "enabled": True,
            "emit_trace_jsonl": True,
            "trace_output_dir": os.getenv("PHASE11B_TRACE_DIR", "artifacts/phase11b/traces"),
        }
    return base


def clip_camera_config(clip_id: str, path: Path) -> dict:
    return {
        "camera_id": clip_id,
        "source_type": "FILE",
        "source_uri": str(path),
        "inference_fps": INFERENCE_FPS,
        "enabled": True,
        "continuity": {"reset_after_s": 5.0},
    }


def zones_for(clip_id: str) -> list[dict]:
    return [
        {
            "zone_id": "CENTRAL_ROI",
            "camera_id": clip_id,
            "name": "central region",
            "polygon": CENTRAL_ROI,
            "enabled": True,
        }
    ]


def main() -> int:
    out = Path(os.getenv("PHASE11_OUTPUT_PATH", "artifacts/phase11/predictions_all.jsonl"))
    run_manifest_path = os.getenv("PHASE11_RUN_MANIFEST_PATH")
    evidence_paths = [out] + ([Path(run_manifest_path)] if run_manifest_path else [])
    existing = [str(path) for path in evidence_paths if path.exists()]
    if existing:
        raise FileExistsError(f"refusing to overwrite inference evidence: {existing}")
    clips = sorted(CLIP_DIR.glob("*.mpg"))
    selected = {name for name in os.getenv("PHASE11_CLIP_NAMES", "").split(",") if name}
    if selected:
        clips = [clip for clip in clips if clip.stem in selected]
    if not clips:
        print("no clips found", file=sys.stderr)
        return 1
    print(f"loading detector ({len(clips)} clips)...", flush=True)
    detector = DEIMv2Detector(**settings.detector_config)
    rules = build_rules()
    all_events: list[dict] = []
    run_clips: list[dict] = []
    started = time.monotonic()

    for clip in clips:
        clip_id = clip.stem
        publisher = CollectingPublisher()
        worker = CVWorker(
            camera_id=clip_id,
            camera_config=clip_camera_config(clip_id, clip),
            detector=detector,
            zones_config=zones_for(clip_id),
            rules_config=rules,
            publisher=publisher,
        )
        t0 = time.monotonic()
        worker.run()
        elapsed = time.monotonic() - t0
        all_events.extend(publisher.events)
        run_clips.append({
            "clip_id": clip_id,
            "source_sha256": hashlib.sha256(clip.read_bytes()).hexdigest(),
            "processed_frames": worker.processed_frames,
            "lifecycle_records": len(publisher.events),
            "completed": True,
        })
        n_starts = sum(1 for e in publisher.events if e.get("event_state") == "START")
        print(f"  {clip_id:26s} frames={worker.processed_frames:5d} "
              f"events={len(publisher.events):3d} starts={n_starts:2d} "
              f"elapsed={elapsed:.1f}s", flush=True)

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as handle:
        for event in all_events:
            handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
    if run_manifest_path:
        core_path = Path("kaggle_pipeline/phase7c_kernel/phase7c_core.py")
        detector_config = settings.detector_config
        checkpoint_path = Path(detector_config["checkpoint_path"])
        backbone_path = Path(detector_config["backbone_path"])
        git_head = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False,
        ).stdout.strip()
        repository_diff = subprocess.run(
            ["git", "diff", "HEAD"], capture_output=True, check=False,
        ).stdout
        git_status = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, check=False,
        ).stdout
        import torch
        run_manifest = {
            "schema": "phase11-inference-run-v1",
            "clips": run_clips,
            "phase7c_valid_floor_roi_polygon": rules["abandoned_object"]["phase7c"].get("valid_floor_roi_polygon"),
            "predictions_path": str(out),
            "predictions_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
            "event_rules_sha256": hashlib.sha256(Path("configs/event_rules.yaml").read_bytes()).hexdigest(),
            "dataset_manifest_sha256": hashlib.sha256(Path("phase8_dataset/manifest.json").read_bytes()).hexdigest(),
            "inference_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "phase7c_core_sha256": hashlib.sha256(core_path.read_bytes()).hexdigest(),
            "repository_diff_sha256": hashlib.sha256(repository_diff).hexdigest(),
            "checkpoint_path": str(checkpoint_path),
            "checkpoint_sha256": hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),
            "backbone_path": str(backbone_path),
            "backbone_sha256": hashlib.sha256(backbone_path.read_bytes()).hexdigest(),
            "git_head": git_head,
            "git_dirty": bool(git_status.strip()),
            "cuda_available": torch.cuda.is_available(),
            "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "phase7c_config_sha256": hashlib.sha256(
                json.dumps(rules["abandoned_object"]["phase7c"], sort_keys=True).encode("utf-8")
            ).hexdigest(),
        }
        manifest_path = Path(run_manifest_path)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with manifest_path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(run_manifest, indent=2))
    print(f"TOTAL lifecycle records: {len(all_events)} -> {out}")
    print(f"total elapsed: {time.monotonic() - started:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
