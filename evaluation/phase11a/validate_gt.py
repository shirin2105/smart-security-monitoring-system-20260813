"""Phase 11A hardened GT validator CLI.

Validates evaluation/phase11a/ground_truth_events.jsonl against the manifest
and clip review status. Exits non-zero on errors. Also usable as a module.

Usage:
    python evaluation/phase11a/validate_gt.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.evaluation.phase11_schema import load_ground_truth
from app.evaluation.phase11a_validate import GroundTruthValidator, load_review_status, validate_review_statuses

HERE = Path(__file__).resolve().parent
GT_PATH = HERE / "ground_truth_events.jsonl"
MANIFEST_PATH = HERE / "manifest.json"
REVIEW_PATH = HERE / "clip_review_status.csv"


def validate() -> list[dict]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    review = load_review_status(REVIEW_PATH)
    durations = {clip["clip_id"]: clip["duration_s"] for clip in manifest.get("clips", [])}
    zones = {clip["clip_id"]: ["CENTRAL_ROI"] for clip in manifest.get("clips", [])}
    validator = GroundTruthValidator(manifest, review_status=review, clip_durations=durations,
                                     zone_by_clip=zones)
    events = load_ground_truth(GT_PATH)
    usable, issues = validator.validate(events)
    issues.extend(validate_review_statuses(review))
    return [issue.to_dict() for issue in issues], len(usable), len(events)


def main() -> int:
    issues, usable, total = validate()
    errors = [issue for issue in issues if issue["severity"] == "error"]
    warnings = [issue for issue in issues if issue["severity"] == "warning"]
    for issue in issues:
        print(f"[{issue['severity'].upper()}] {issue['clip_id']} {issue.get('event_id') or ''}: {issue['message']}")
    print(f"validated {total} events -> {usable} usable; {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
