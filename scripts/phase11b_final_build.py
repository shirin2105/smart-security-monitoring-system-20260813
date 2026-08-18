"""Create the fail-closed Phase 11B-FINAL abandoned-policy refreeze."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

OUT = Path("evaluation/phase11b_final")
ARTIFACTS = Path("artifacts/phase11b_final")
CLIPS = ("LeftBag", "LeftBag_AtChair", "LeftBag_PickedUp", "LeftBox")
CENTRAL_ROI = [[115, 115], [269, 115], [269, 259], [115, 259]]


def require_absent(paths: list[Path]) -> None:
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        raise FileExistsError(f"refusing to overwrite Phase 11B-FINAL evidence: {existing}")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def generic_negative_ids(manifest: dict) -> list[str]:
    return sorted(clip["clip_id"] for clip in manifest["clips"]
                  if "abandoned_negative" in clip["scenario_tags"])


def validate_decisions(rows: list[dict]) -> None:
    allowed = {"IN_POLICY_POSITIVE", "OUT_OF_POLICY_GT", "MISLABELED_NON_ABANDONED", "AMBIGUOUS_NEEDS_HUMAN"}
    if {row["clip_id"] for row in rows} != set(CLIPS):
        raise ValueError("adjudication must cover exactly the four required clips")
    if any(row["adjudication_status"] not in allowed for row in rows):
        raise ValueError("invalid adjudication status")
    for row in rows:
        expected_in_policy = row["adjudication_status"] == "IN_POLICY_POSITIVE"
        if bool(row["is_in_policy"]) != expected_in_policy:
            raise ValueError("adjudication status contradicts is_in_policy")
        if row["adjudication_status"] != "IN_POLICY_POSITIVE" and row.get("roi_change_required"):
            raise ValueError("excluded/ambiguous clips cannot authorize an ROI change")


def _contact_sheet(clip_id: str, event: dict) -> Path:
    capture = cv2.VideoCapture(str(Path("phase8_dataset/videos") / f"{clip_id}.mpg"))
    fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    event_times = [max(0.0, event["start_s"] - 3), event["start_s"], event["trigger_time_s"],
                   event["end_s"], min((total - 1) / fps, event["end_s"] + 5)]
    images = []
    for time_s in event_times:
        capture.set(cv2.CAP_PROP_POS_FRAMES, min(total - 1, int(time_s * fps)))
        ok, frame = capture.read()
        if not ok:
            raise RuntimeError(f"failed to read {clip_id} at {time_s:.2f}s")
        cv2.polylines(frame, [np.asarray(CENTRAL_ROI, dtype=np.int32)], True, (0, 255, 255), 2)
        cv2.putText(frame, f"{clip_id} t={time_s:.2f}s", (8, 18), cv2.FONT_HERSHEY_SIMPLEX, .45, (255, 255, 255), 2)
        images.append(frame)
    capture.release()
    sheet = np.hstack(images)
    path = ARTIFACTS / "review" / f"{clip_id}-timeline.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), sheet):
        raise RuntimeError(f"failed to write {path}")
    return path


def build() -> dict:
    output_paths = [OUT / name for name in (
        "adjudication.csv", "refrozen_manifest.json", "refrozen_ground_truth_events.jsonl",
        "roi_policy.json", "changelog.csv",
    )]
    output_paths += [ARTIFACTS / "review" / f"{clip_id}-timeline.png" for clip_id in CLIPS]
    require_absent(output_paths)
    OUT.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    gt = {row["clip_id"]: row for row in read_jsonl(Path("evaluation/phase11a/ground_truth_events.jsonl"))
          if row["event_type"] == "ABANDONED_OBJECT"}
    decisions = []
    for clip_id in CLIPS:
        review_path = _contact_sheet(clip_id, gt[clip_id])
        decisions.append({
            "clip_id": clip_id, "gt_event_id": gt[clip_id]["event_id"],
            "adjudication_status": "AMBIGUOUS_NEEDS_HUMAN", "is_in_policy": False,
            "roi_change_required": False, "visual_review_status": "AGENT_EVIDENCE_ONLY_HUMAN_REQUIRED",
            "decision_reason": "Product alert coverage cannot be inferred from video content or filename",
            "evidence": str(review_path),
            "next_action": "Human product owner must mark IN_POLICY/OUT_OF_POLICY/MISLABELED",
        })
    validate_decisions(decisions)
    with (OUT / "adjudication.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(decisions[0]))
        writer.writeheader(); writer.writerows(decisions)
    dataset = json.loads(Path("phase8_dataset/manifest.json").read_text(encoding="utf-8"))
    manifest = {
        "version": "phase11b-final-v1", "status": "ROI_POLICY_UNRESOLVED",
        "positive_clips": [], "generic_negative_clips": generic_negative_ids(dataset),
        "excluded_pending_human": list(CLIPS), "source_manifest": "phase8_dataset/manifest.json",
    }
    (OUT / "refrozen_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (OUT / "refrozen_ground_truth_events.jsonl").write_text("", encoding="utf-8")
    policy = {
        "version": "phase11b-final-roi-v1", "status": "UNCHANGED_PENDING_HUMAN",
        "event_type": "ABANDONED_OBJECT", "coordinate_mode": "pixel",
        "default_polygon": CENTRAL_ROI, "camera_overrides": {},
        "diagnostic_no_roi_is_production_default": False,
        "source": "docs/phase11/BENCHMARK_FREEZE.md",
    }
    (OUT / "roi_policy.json").write_text(json.dumps(policy, indent=2), encoding="utf-8")
    changelog = "action,scope,reason\ncreated,phase11b-final-v1,non-destructive policy refreeze\nexcluded,4 positives,pending human product adjudication\npreserved,CENTRAL_ROI,frozen production benchmark policy\n"
    (OUT / "changelog.csv").write_text(changelog, encoding="utf-8")
    return {"decisions": decisions, "manifest": manifest, "policy": policy}


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
