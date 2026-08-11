import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[2] / "tools" / "dataset" / "validate_coco_custom.py"
SPEC = importlib.util.spec_from_file_location("validate_coco_custom", SCRIPT_PATH)
validator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validator)


def write_split(root: Path, split: str, images, annotations, categories) -> None:
    (root / "images" / split).mkdir(parents=True)
    for image in images:
        (root / "images" / split / image["file_name"]).write_bytes(b"image")
    annotations_root = root / "annotations"
    annotations_root.mkdir(exist_ok=True)
    (annotations_root / f"instances_{split}.json").write_text(
        json.dumps({"images": images, "annotations": annotations, "categories": categories}), encoding="utf-8"
    )


def test_validator_detects_coco_errors_and_split_leakage(tmp_path: Path):
    categories = [{"id": 1, "name": "person"}]
    train_images = [{"id": 1, "file_name": "one.jpg", "width": 10, "height": 10, "video_id": "shared"}]
    train_annotations = [
        {"id": 1, "image_id": 1, "category_id": 9, "bbox": [-1, 0, 0, 4]},
        {"id": 1, "image_id": 2, "category_id": 1, "bbox": [0, 0, 4, 4]},
    ]
    write_split(tmp_path, "train", train_images, train_annotations, categories)
    write_split(tmp_path, "val", [{"id": 2, "file_name": "two.jpg", "width": 10, "height": 10, "video_id": "shared"}], [], categories)
    write_split(tmp_path, "test", [{"id": 3, "file_name": "three.jpg", "width": 10, "height": 10, "video_id": "test"}], [], categories)

    report = validator.validate_dataset(tmp_path)

    assert not report["valid"]
    assert report["splits"]["train"]["errors"]["duplicate_annotation_ids"] == [1]
    assert report["splits"]["train"]["errors"]["invalid_category_ids"] == [1]
    assert report["splits"]["train"]["errors"]["zero_size_bboxes"] == [1]
    assert report["splits"]["train"]["errors"]["out_of_bounds_bboxes"] == [1]
    assert report["splits"]["train"]["errors"]["orphan_annotations"] == [1]
    assert report["split_overlap"]["video_ids"]["train_val"] == ["shared"]


def test_validator_keeps_pixel_bucket_boundaries():
    assert validator.bucket(7.99, validator.PIXEL_BUCKETS) == "lt_8"
    assert validator.bucket(8, validator.PIXEL_BUCKETS) == "8_to_16"
    assert validator.bucket(16, validator.PIXEL_BUCKETS) == "8_to_16"
    assert validator.bucket(16.01, validator.PIXEL_BUCKETS) == "16_to_32"
    assert validator.bucket(32, validator.PIXEL_BUCKETS) == "16_to_32"
    assert validator.bucket(32.01, validator.PIXEL_BUCKETS) == "gt_32"


def test_validator_rejects_splits_without_group_identity(tmp_path: Path):
    categories = [{"id": 1, "name": "person"}]
    for index, split in enumerate(("train", "val", "test"), start=1):
        write_split(tmp_path, split, [{"id": index, "file_name": f"{split}.jpg", "width": 10, "height": 10}], [], categories)

    report = validator.validate_dataset(tmp_path)

    assert not report["valid"]
    assert report["split_identity_field"] is None
