"""Product Policy v2 — local-clip re-evaluation harness.

Enumerates the repo-relative ``tests/clips`` folder, runs the unified CV worker
(DEIMv2 + ByteTrack) over each clip, and emits:

  * ``artifacts/product_policy_v2/local_clip_inventory.json``
  * ``artifacts/product_policy_v2/review/<clip>/summary.json``
  * ``artifacts/product_policy_v2/review/<clip>/events.jsonl``

Per Product Policy v2 the worker runs with:
  * ABANDONED_OBJECT over the full frame (no valid-floor ROI),
  * CROWD_THRESHOLD over the full frame (no per-zone ROI),
  * ZONE_INTRUSION only (zones still used, but none are configured for these clips).

Run under the deimv2 venv (torch/CUDA):

    third_party\\deimv2\\.python311\\python.exe scripts/product_policy_v2_local_clip_eval.py

Override the clips directory with ``PP2_CLIPS_DIR`` (repo-relative).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

CLIPS_DIR = Path(os.getenv("PP2_CLIPS_DIR", "tests/clips"))
OUT_DIR = Path(os.getenv("PP2_OUT_DIR", "artifacts/product_policy_v2"))
INFERENCE_FPS = float(os.getenv("PP2_INFERENCE_FPS", "5.0"))

# Trusted Phase-8/11 adjudication (do not tune against these).
TRUSTED_PHASE8 = {
    "LeftBag": "POSITIVE",
    "LeftBag_AtChair": "POSITIVE",
    "LeftBag_PickedUp": "NEGATIVE",
    "LeftBox": "EXCLUDE_AMBIGUOUS",
    "LeftBag_BehindChair": "EXCLUDE_UNREVIEWED",
}

# Tier A: required primary abandoned evaluation set.
TIER_A_PATTERNS = ["*ABODA*", "abandoned_object_demo.mp4", "aban3.mp4", "pets2006_3.mp4"]
TIER_B_KNOWN = [
    "bottle-detection.mp4",
    "people_detection.mp4",
    "store-aisle-detection.mp4",
    "walking_people.mp4",
]

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


def build_rules() -> dict:
    from app.config import settings
    from scripts.phase11_infer import _phase7c_config

    return {
        "intrusion": INTRUSION_RULES,
        "crowd": CROWD_RULES,
        "abandoned_object": {"phase7c": _phase7c_config()},
    }


def video_metadata(path: Path) -> dict:
    """Best-effort metadata without running the detector."""
    meta: dict = {"duration_s": None, "fps": None, "frame_count": None}
    try:
        import cv2

        cap = cv2.VideoCapture(str(path))
        if cap.isOpened():
            meta["fps"] = float(cap.get(cv2.CAP_PROP_FPS)) or None
            meta["frame_count"] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or None
            f = meta["fps"] or 0.0
            if f > 0 and meta["frame_count"]:
                meta["duration_s"] = round(meta["frame_count"] / f, 3)
            cap.release()
    except Exception as exc:  # pragma: no cover - cv2 optional
        meta["error"] = f"metadata_unavailable: {exc}"
    return meta


def clip_role(name: str) -> tuple[str, str]:
    low = name.lower()
    if any(Path(p).name == name or ("aboda" in low) for p in TIER_A_PATTERNS):
        return "TIER_A", "UNREVIEWED"
    if name in TIER_B_KNOWN:
        return "TIER_B", "UNREVIEWED"
    return "GENERAL_REGRESSION", "UNREVIEWED"


def run_inference_for_clip(clip: Path, rules: dict):
    """Run the unified worker over one clip. Returns (events, error)."""
    from app.cv.detector import DEIMv2Detector
    from app.cv.worker import CVWorker
    from app.config import settings

    class _CollectingPublisher:
        def __init__(self) -> None:
            self.events: list[dict] = []

        def publish(self, event) -> bool:
            self.events.append(event.to_dict())
            return True

    camera_config = {
        "camera_id": clip.stem,
        "source_type": "FILE",
        "source_uri": str(clip),
        "inference_fps": INFERENCE_FPS,
        "enabled": True,
        "continuity": {"reset_after_s": 5.0},
    }
    publisher = _CollectingPublisher()
    worker = CVWorker(
        camera_id=clip.stem,
        camera_config=camera_config,
        detector=DEIMv2Detector(**settings.detector_config),
        zones_config=[],  # no intrusion zones configured for local clips
        rules_config=rules,
        publisher=publisher,
    )
    worker.run()
    return publisher.events, None


def summarize_events(events: list[dict]) -> dict:
    abandoned = [e for e in events if e.get("event_type") == "ABANDONED_OBJECT"]
    starts = [e for e in abandoned if e.get("event_state") == "START"]
    ends = [e for e in abandoned if e.get("event_state") == "END"]
    first_start = min((e.get("event_time") for e in starts), default=None)
    owner_ids = sorted(
        {e["objects"].get("owner", {}).get("person_track_id") for e in abandoned if e.get("objects", {}).get("owner")}
    )
    physical_ids = sorted({e.get("entity_key") for e in abandoned})
    return {
        "abandoned_start_count": len(starts),
        "abandoned_end_count": len(ends),
        "first_start_s": first_start,
        "physical_luggage_ids": physical_ids,
        "owner_associated": bool(owner_ids),
        "owner_track_ids": owner_ids,
        "crowd_active_count": sum(1 for e in events if e.get("event_type") == "CROWD_THRESHOLD" and e.get("event_state") == "START"),
        "intrusion_active_count": sum(1 for e in events if e.get("event_type") == "ZONE_INTRUSION" and e.get("event_state") == "START"),
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    review_dir = OUT_DIR / "review"
    review_dir.mkdir(parents=True, exist_ok=True)

    present = (
        sorted(
            [p for ext in ("*.mp4", "*.mpg", "*.avi", "*.webm", "*.mov")
             for p in CLIPS_DIR.glob(ext)]
        )
        if CLIPS_DIR.exists()
        else []
    )
    present_names = {p.name for p in present}

    selected = {n for n in os.getenv("PP2_CLIP_NAMES", "").split(",") if n}
    if selected:
        present = [p for p in present if p.name in selected]

    inventory: list[dict] = []
    clip_results: list[dict] = []

    # Present clips.
    for clip in present:
        role, adjudication = clip_role(clip.name)
        meta = video_metadata(clip)
        entry = {
            "file_name": clip.name,
            "relative_path": str(clip),
            "size_bytes": clip.stat().st_size,
            "present": True,
            "duration_s": meta.get("duration_s"),
            "fps": meta.get("fps"),
            "frame_count": meta.get("frame_count"),
            "assigned_role": role,
            "adjudication_status": adjudication,
            "inference_status": "pending",
        }
        inventory.append(entry)

    # Missing Tier A clips -> must be reported MISSING.
    for pat in TIER_A_PATTERNS:
        if pat == "*ABODA*":
            if not any("aboda" in n.lower() for n in present_names):
                inventory.append({
                    "file_name": "ABODA clips",
                    "relative_path": None,
                    "size_bytes": None,
                    "present": False,
                    "duration_s": None,
                    "fps": None,
                    "frame_count": None,
                    "assigned_role": "TIER_A",
                    "adjudication_status": "UNREVIEWED",
                    "inference_status": "MISSING",
                })
            continue
        if pat not in present_names:
            inventory.append({
                "file_name": pat,
                "relative_path": None,
                "size_bytes": None,
                "present": False,
                "duration_s": None,
                "fps": None,
                "frame_count": None,
                "assigned_role": "TIER_A",
                "adjudication_status": "UNREVIEWED",
                "inference_status": "MISSING",
            })

    # Write the inventory up front so it survives even if inference is unavailable.
    inventory_path = OUT_DIR / "local_clip_inventory.json"
    inventory_path.write_text(json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8")

    skip_inference = os.getenv("PP2_SKIP_INFERENCE") == "1"

    # Attempt real inference.
    rules = build_rules()
    for clip in present:
        entry = next(e for e in inventory if e["file_name"] == clip.name)
        if skip_inference:
            entry["inference_status"] = "skipped_by_flag"
            clip_results.append({"clip": clip.name, "status": "skipped_by_flag"})
            continue
        try:
            events, err = run_inference_for_clip(clip, rules)
        except Exception as exc:  # detector/model/GPU may be unavailable
            entry["inference_status"] = f"skipped: {type(exc).__name__}: {exc}"
            clip_results.append({"clip": clip.name, "error": entry["inference_status"]})
            inventory_path.write_text(json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8")
            continue

        summary = summarize_events(events)
        summary.update({
            "clip": clip.name,
            "duration_s": entry.get("duration_s"),
            "detected_luggage": len(summary.pop("physical_luggage_ids")),
            "review_status": "UNREVIEWED",
            "notes": "auto-generated; do not infer GT from filename",
        })
        review_clip_dir = review_dir / clip.stem
        review_clip_dir.mkdir(parents=True, exist_ok=True)
        (review_clip_dir / "summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        abandoned_events = [e for e in events if e.get("event_type") == "ABANDONED_OBJECT"]
        with (review_clip_dir / "events.jsonl").open("w", encoding="utf-8") as fh:
            for e in abandoned_events:
                fh.write(json.dumps(e, ensure_ascii=False, separators=(",", ":")) + "\n")

        entry["inference_status"] = "completed"
        entry["abandoned_start_count"] = summary["abandoned_start_count"]
        entry["first_start_s"] = summary["first_start_s"]
        clip_results.append({
            "clip": clip.name,
            "abandoned_start_count": summary["abandoned_start_count"],
            "first_start_s": summary["first_start_s"],
            "crowd_active_count": summary["crowd_active_count"],
            "intrusion_active_count": summary["intrusion_active_count"],
        })
        print(f"  {clip.name:28s} abandoned_starts={summary['abandoned_start_count']:2d} "
              f"first_start={summary['first_start_s']}", flush=True)
        inventory_path.write_text(json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8")

    inventory_path = OUT_DIR / "local_clip_inventory.json"
    inventory_path.write_text(json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "local_clip_eval_results.json").write_text(
        json.dumps(clip_results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"inventory -> {inventory_path}")
    print(f"results   -> {OUT_DIR / 'local_clip_eval_results.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
