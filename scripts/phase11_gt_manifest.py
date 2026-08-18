"""Phase 11: build manifest.json + ground_truth_events.jsonl from CAVIAR clips.

Runs under the test venv (no model needed). GT is derived deterministically from
CAVIAR trajectory XML via the Phase 11 extractor.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

import cv2

from app.evaluation.phase11_gt_extractor import GroundTruthExtractor

CLIP_DIR = Path("phase8_dataset/videos")
XML_DIR = Path("phase8_dataset/source_xml")
MANIFEST_PATH = Path("evaluation/phase11/manifest.json")
GT_PATH = Path("evaluation/phase11/ground_truth_events.jsonl")


def _clip_duration(path: Path) -> float:
    cap = cv2.VideoCapture(str(path))
    count = 0
    while True:
        ok, _ = cap.read()
        if not ok:
            break
        count += 1
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    cap.release()
    return count / fps if fps > 0 else 0.0


def _clip_tags(clip_id: str, events: list) -> list[str]:
    per_event = Counter(e.event_type for e in events)
    tags = []
    for event_type, count in per_event.items():
        tags.append("positive" if count > 0 else "negative")
        tags.append(event_type.lower())
    if clip_id.startswith(("LeftBag", "LeftBox")):
        tags.append("hard-small-object")
    return sorted(set(tags))


def main() -> int:
    clips = sorted(CLIP_DIR.glob("*.mpg"))
    if not clips:
        print("no clips", file=sys.stderr)
        return 1
    extractor = GroundTruthExtractor()
    manifest_clips = []
    all_gt = []
    for clip in clips:
        clip_id = clip.stem
        xml_path = XML_DIR / f"{clip_id}.xml"
        events = extractor.extract(clip_id, clip_id, xml_path) if xml_path.exists() else []
        all_gt.extend(events)
        manifest_clips.append(
            {
                "clip_id": clip_id,
                "camera_id": clip_id,
                "video_path": str(clip),
                "duration_s": round(_clip_duration(clip), 3),
                "event_targets": sorted({e.event_type for e in events}),
                "tags": _clip_tags(clip_id, events),
            }
        )

    manifest = {
        "benchmark_version": "phase11-v1",
        "clips": manifest_clips,
        "gt_source": "CAVIAR trajectory XML (heuristic, provisional)",
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    GT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with GT_PATH.open("w", encoding="utf-8") as handle:
        for event in all_gt:
            handle.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")

    counts = Counter(e.event_type for e in all_gt)
    print(f"clips: {len(manifest_clips)}")
    print(f"GT events: {sum(counts.values())} {dict(counts)}")
    print(f"manifest -> {MANIFEST_PATH}")
    print(f"gt -> {GT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
