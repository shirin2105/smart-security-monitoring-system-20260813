"""Consolidate Product Policy v2 local-clip results into a single inventory.

Reads the per-clip review summaries produced by
``scripts/product_policy_v2_local_clip_eval.py`` and merges them into
``artifacts/product_policy_v2/local_clip_inventory.json`` + a results table.
Use this instead of re-running inference when only the consolidated view is
needed.

    third_party\\deimv2\\.python311\\python.exe scripts/consolidate_product_policy_v2_results.py
"""

from __future__ import annotations

import json
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.product_policy_v2_local_clip_eval import (
    CLIPS_DIR,
    OUT_DIR,
    TIER_A_PATTERNS,
    TIER_B_KNOWN,
    clip_role,
    video_metadata,
)

REVIEW_DIR = OUT_DIR / "review"


def main() -> int:
    present = sorted(
        [p for ext in ("*.mp4", "*.mpg", "*.avi", "*.webm", "*.mov") for p in CLIPS_DIR.glob(ext)]
    ) if CLIPS_DIR.exists() else []
    present_names = {p.name for p in present}

    inventory: list[dict] = []
    results: list[dict] = []

    for clip in present:
        role, adjudication = clip_role(clip.name)
        meta = video_metadata(clip)
        summary_path = REVIEW_DIR / clip.stem / "summary.json"
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
        }
        if summary_path.exists():
            s = json.loads(summary_path.read_text(encoding="utf-8"))
            entry["inference_status"] = "completed"
            entry["abandoned_start_count"] = s.get("abandoned_start_count")
            entry["first_start_s"] = s.get("first_start_s")
            entry["owner_associated"] = s.get("owner_associated")
            entry["crowd_active_count"] = s.get("crowd_active_count")
            entry["intrusion_active_count"] = s.get("intrusion_active_count")
            results.append({
                "clip": clip.name,
                "abandoned_start_count": s.get("abandoned_start_count"),
                "first_start_s": s.get("first_start_s"),
                "crowd_active_count": s.get("crowd_active_count"),
                "intrusion_active_count": s.get("intrusion_active_count"),
                "review_status": s.get("review_status", "UNREVIEWED"),
            })
        else:
            entry["inference_status"] = "not_run"
            results.append({"clip": clip.name, "status": "not_run"})
        inventory.append(entry)

    # Missing Tier A clips.
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

    inventory_path = OUT_DIR / "local_clip_inventory.json"
    inventory_path.write_text(json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "local_clip_eval_results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"consolidated inventory -> {inventory_path}")
    print(f"clips reviewed: {sum(1 for e in inventory if e.get('inference_status') == 'completed')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
