"""Generate a manual-review hard-case manifest from a COCO annotation file."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


UNKNOWN_FIELDS = (
    "camera_angle", "distance", "lighting", "motion_blur",
    "background_similarity", "object_near_person", "object_on_floor",
    "previous_detector_missed",
)


def build_samples(annotation_path: Path) -> list[dict]:
    dataset = json.loads(annotation_path.read_text(encoding="utf-8"))
    occlusion = defaultdict(bool)
    for annotation in dataset.get("annotations", []):
        occlusion[annotation["image_id"]] |= bool(annotation.get("occluded", False))
    samples = []
    for image in dataset.get("images", []):
        sample = {
            "image_id": image["id"],
            "file_name": image["file_name"],
            "video_id": image.get("video_id", "UNKNOWN"),
            "occluded": occlusion[image["id"]],
            **{field: "UNKNOWN" for field in UNKNOWN_FIELDS},
            "annotation_status": "PENDING_MANUAL_REVIEW",
        }
        samples.append(sample)
    return samples


def write_status(samples: list[dict], status_path: Path) -> None:
    lines = ["# Hard-case metadata status", "", f"- Total images: {len(samples)}", "- Manually reviewed samples: 0", "- Available for evaluation now: `occluded`", "- Unavailable pending manual review: " + ", ".join(UNKNOWN_FIELDS), ""]
    for field in ("occluded", *UNKNOWN_FIELDS):
        known = sum(sample[field] != "UNKNOWN" for sample in samples)
        lines.append(f"- `{field}`: {known} labeled, {len(samples) - known} UNKNOWN")
    status_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", type=Path, default=Path("third_party/deimv2/dataset/annotations/instances_test.json"))
    parser.add_argument("--output", type=Path, default=Path("evaluation/hard_cases_template.json"))
    parser.add_argument("--csv", type=Path, default=Path("evaluation/hard_cases_labeling.csv"))
    parser.add_argument("--status", type=Path, default=Path("reports/hard_case_metadata_status.md"))
    args = parser.parse_args()
    samples = build_samples(args.annotations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    args.status.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(samples, indent=2) + "\n", encoding="utf-8")
    with args.csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=samples[0].keys())
        writer.writeheader()
        writer.writerows(samples)
    write_status(samples, args.status)
    print(f"Wrote {len(samples)} pending-review samples")


if __name__ == "__main__":
    main()
