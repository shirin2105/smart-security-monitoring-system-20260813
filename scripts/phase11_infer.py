"""Phase 11 real inference: run the unified CV worker over CAVIAR clips.

Runs under the deimv2 venv (torch/CUDA). Produces canonical cv-event-v1 records
in ``artifacts/phase11/predictions_all.jsonl`` (one line per lifecycle record).

Usage:
    third_party\\deimv2\\.python311\\python.exe scripts/phase11_infer.py
"""

from __future__ import annotations

import json
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
    base["valid_floor_roi_polygon"] = CENTRAL_ROI
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
    clips = sorted(CLIP_DIR.glob("*.mpg"))
    if not clips:
        print("no clips found", file=sys.stderr)
        return 1
    print(f"loading detector ({len(clips)} clips)...", flush=True)
    detector = DEIMv2Detector(**settings.detector_config)
    rules = build_rules()
    all_events: list[dict] = []
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
        n_starts = sum(1 for e in publisher.events if e.get("event_state") == "START")
        print(f"  {clip_id:26s} frames={worker.processed_frames:5d} "
              f"events={len(publisher.events):3d} starts={n_starts:2d} "
              f"elapsed={elapsed:.1f}s", flush=True)

    out = Path("artifacts/phase11/predictions_all.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for event in all_events:
            handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"TOTAL lifecycle records: {len(all_events)} -> {out}")
    print(f"total elapsed: {time.monotonic() - started:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
