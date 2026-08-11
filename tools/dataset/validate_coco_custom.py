"""Validate a custom COCO dataset and write reproducible quality reports."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SPLITS = ("train", "val", "test")
PIXEL_BUCKETS = (("lt_8", 0, 8), ("8_to_16", 8, 16), ("16_to_32", 16, 32), ("gt_32", 32, None))
AREA_BUCKETS = (("lt_8", 0, 8), ("8_to_16", 8, 16), ("16_to_32", 16, 32), ("gt_32", 32, None))
COCO_SIZE_BUCKETS = (("small", 0, 32**2), ("medium", 32**2, 96**2), ("large", 96**2, None))


def bucket(value: float, buckets: tuple[tuple[str, float, float | None], ...]) -> str:
    if buckets in (PIXEL_BUCKETS, AREA_BUCKETS):
        if value < 8:
            return "lt_8"
        if value <= 16:
            return "8_to_16"
        if value <= 32:
            return "16_to_32"
        return "gt_32"
    for name, lower, upper in buckets:
        if value >= lower and (upper is None or value < upper):
            return name
    raise ValueError(f"Value cannot be bucketed: {value}")


def duplicate_ids(records: list[dict[str, Any]]) -> list[Any]:
    ids = [record.get("id") for record in records]
    return [item for item, count in Counter(ids).items() if count > 1]


def validate_split(dataset_root: Path, split: str) -> dict[str, Any]:
    annotation_path = dataset_root / "annotations" / f"instances_{split}.json"
    image_root = dataset_root / "images" / split
    document = json.loads(annotation_path.read_text(encoding="utf-8"))
    images = [item for item in document.get("images", []) if isinstance(item, dict)]
    annotations = [item for item in document.get("annotations", []) if isinstance(item, dict)]
    categories = [item for item in document.get("categories", []) if isinstance(item, dict)]
    image_ids = {image.get("id") for image in images}
    image_by_id = {image.get("id"): image for image in images}
    category_ids = {category.get("id") for category in categories}
    errors: dict[str, list[Any]] = defaultdict(list)
    by_category: Counter[str] = Counter()
    width_buckets: Counter[str] = Counter()
    height_buckets: Counter[str] = Counter()
    area_buckets: Counter[str] = Counter()
    coco_size_buckets: Counter[str] = Counter()
    objects_per_image: Counter[Any] = Counter()
    occluded = 0

    for image in images:
        file_name = image.get("file_name")
        if not file_name or not (image_root / file_name).is_file():
            errors["missing_images"].append(file_name)
    errors["duplicate_image_ids"] = duplicate_ids(images)
    errors["duplicate_annotation_ids"] = duplicate_ids(annotations)

    for annotation in annotations:
        annotation_id = annotation.get("id")
        image_id = annotation.get("image_id")
        category_id = annotation.get("category_id")
        if image_id not in image_ids:
            errors["orphan_annotations"].append(annotation_id)
            continue
        if category_id not in category_ids:
            errors["invalid_category_ids"].append(annotation_id)
        bbox = annotation.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            errors["invalid_bboxes"].append(annotation_id)
            continue
        x, y, width, height = bbox
        if not all(isinstance(value, (int, float)) for value in bbox):
            errors["invalid_bboxes"].append(annotation_id)
            continue
        if width == 0 or height == 0:
            errors["zero_size_bboxes"].append(annotation_id)
        image = image_by_id[image_id]
        if not isinstance(image.get("width"), (int, float)) or not isinstance(image.get("height"), (int, float)):
            errors["invalid_image_dimensions"].append(image_id)
            continue
        if x < 0 or y < 0 or width < 0 or height < 0 or x + width > image["width"] or y + height > image["height"]:
            errors["out_of_bounds_bboxes"].append(annotation_id)
            continue
        if category_id in category_ids and width > 0 and height > 0:
            bbox_area = width * height
            width_buckets[bucket(width, PIXEL_BUCKETS)] += 1
            height_buckets[bucket(height, PIXEL_BUCKETS)] += 1
            area_buckets[bucket(bbox_area, AREA_BUCKETS)] += 1
            coco_size_buckets[bucket(bbox_area, COCO_SIZE_BUCKETS)] += 1
            by_category[str(category_id)] += 1
            objects_per_image[image_id] += 1
            occluded += bool(annotation.get("occluded", False))

    video_ids = {image.get("video_id") for image in images if image.get("video_id") is not None}
    group_fields = ("video_id", "camera_id", "camera", "scene_id", "scene")
    groups = {field: sorted({str(image[field]) for image in images if image.get(field) is not None}) for field in group_fields}
    return {
        "annotation_file": str(annotation_path),
        "images": len(images),
        "annotations": len(annotations),
        "categories": categories,
        "video_ids": sorted(video_ids),
        "groups": groups,
        "errors": dict(errors),
        "empty_images": sum(image["id"] not in objects_per_image for image in images),
        "empty_image_ratio": sum(image["id"] not in objects_per_image for image in images) / len(images) if images else 0,
        "objects_per_class": dict(sorted(by_category.items(), key=lambda item: int(item[0]))),
        "bbox_width_pixels": dict(width_buckets),
        "bbox_height_pixels": dict(height_buckets),
        "bbox_area_pixels": dict(area_buckets),
        "bbox_coco_size": dict(coco_size_buckets),
        "occluded_objects": occluded,
        "occlusion_metadata_present": any("occluded" in annotation for annotation in annotations),
    }


def validate_dataset(dataset_root: Path, config_path: Path | None = None) -> dict[str, Any]:
    splits = {split: validate_split(dataset_root, split) for split in SPLITS}
    category_sets = {split: [(item.get("id"), item.get("name")) for item in data["categories"]] for split, data in splits.items()}
    category_mismatches = {split: values for split, values in category_sets.items() if values != category_sets["train"]}
    all_images = [image for data in splits.values() for image in json.loads(Path(data["annotation_file"]).read_text(encoding="utf-8")).get("images", []) if isinstance(image, dict)]
    identity_fields = ("video_id", "camera_id", "camera", "scene_id", "scene")
    identity_field = next((field for field in identity_fields if all_images and all(image.get(field) is not None for image in all_images)), None)
    overlaps: dict[str, dict[str, list[str]]] = {}
    for field in ("video_ids", "camera_id", "camera", "scene_id", "scene"):
        values = {split: set(data["video_ids"] if field == "video_ids" else data["groups"][field]) for split, data in splits.items()}
        overlaps[field] = {f"{left}_{right}": sorted(values[left] & values[right]) for left, right in (("train", "val"), ("train", "test"), ("val", "test"))}
    config_errors: list[str] = []
    config = {}
    if config_path is not None:
        config_text = config_path.read_text(encoding="utf-8")
        configured_ids = [int(value) for value in re.search(r"^category_ids:\s*\[([^]]*)\]", config_text, re.MULTILINE).group(1).split(",")]
        config = {"path": str(config_path), "category_ids": configured_ids}
        if configured_ids != [item[0] for item in category_sets["train"]]:
            config_errors.append("category_ids do not match annotation categories")
        if not re.search(r"^remap_mscoco_category:\s*False\s*$", config_text, re.MULTILINE):
            config_errors.append("remap_mscoco_category must be False")
    valid = identity_field is not None and not config_errors and not category_mismatches and all(not values for field in overlaps.values() for values in field.values()) and all(
        not issue for data in splits.values() for issue in data["errors"].values()
    )
    return {"dataset_root": str(dataset_root), "valid": valid, "split_identity_field": identity_field, "category_mismatches": category_mismatches, "config": config, "config_errors": config_errors, "split_overlap": overlaps, "splits": splits}


def markdown_report(report: dict[str, Any]) -> str:
    lines = ["# Custom COCO dataset validation", "", f"**Status:** {'PASS' if report['valid'] else 'FAIL'}", ""]
    for split, data in report["splits"].items():
        lines.extend([f"## {split}", "", f"- Images: {data['images']}", f"- Annotations: {data['annotations']}", f"- Empty images: {data['empty_images']} ({data['empty_image_ratio']:.2%})", f"- Occluded objects: {data['occluded_objects'] if data['occlusion_metadata_present'] else 'metadata unavailable'}", f"- Objects per class: {data['objects_per_class']}", f"- Width px: {data['bbox_width_pixels']}", f"- Height px: {data['bbox_height_pixels']}", f"- Area px²: {data['bbox_area_pixels']}", f"- COCO size: {data['bbox_coco_size']}", f"- Validation errors: {sum(len(items) for items in data['errors'].values())}", ""])
    lines.extend(["## Split leakage", "", f"```json\n{json.dumps(report['split_overlap'], indent=2)}\n```", "", "## Category consistency", "", f"```json\n{json.dumps(report['category_mismatches'], indent=2)}\n```"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=Path("third_party/deimv2/dataset"))
    parser.add_argument("--report-dir", type=Path, default=Path("reports"))
    parser.add_argument("--config-path", type=Path, default=Path("third_party/deimv2/configs/dataset/custom_detection.yml"))
    args = parser.parse_args()
    report = validate_dataset(args.dataset_root, args.config_path)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    (args.report_dir / "dataset_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (args.report_dir / "dataset_report.md").write_text(markdown_report(report), encoding="utf-8")
    print(f"Validation {'passed' if report['valid'] else 'failed'}; reports written to {args.report_dir}")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
