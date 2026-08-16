"""Generate Phase 11B.2 ROI audit rows and diagnostic overlays."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kaggle_pipeline.phase7c_kernel.phase7c_core import point_in_polygon


CLIPS = ("LeftBag", "LeftBag_AtChair", "LeftBag_PickedUp", "LeftBox")
CENTRAL_ROI = [[115.0, 115.0], [269.0, 115.0], [269.0, 259.0], [115.0, 259.0]]
ROOT = Path("artifacts/phase11b2")


def resolve_roi_points(points, mode: str, width: int, height: int):
    if points is None:
        return None
    if len(points) < 3 or any(len(point) != 2 for point in points):
        raise ValueError("ROI must contain at least three x/y points")
    if mode == "pixel":
        return [[float(x), float(y)] for x, y in points]
    if mode == "normalized":
        if any(not 0 <= value <= 1 for point in points for value in point):
            raise ValueError("normalized ROI values must be within [0, 1]")
        return [[float(x) * width, float(y) * height] for x, y in points]
    raise ValueError(f"unsupported ROI coordinate mode: {mode}")


def restore_letterbox_bbox(box, scale: float, pad_x: float, pad_y: float):
    if scale <= 0:
        raise ValueError("letterbox scale must be positive")
    x1, y1, x2, y2 = map(float, box)
    return [(x1 - pad_x) / scale, (y1 - pad_y) / scale,
            (x2 - pad_x) / scale, (y2 - pad_y) / scale]


def bbox_points(box):
    x1, y1, x2, y2 = map(float, box)
    return [(x1 + x2) / 2.0, (y1 + y2) / 2.0], [(x1 + x2) / 2.0, y2]


def _read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _gt_events():
    path = Path("evaluation/phase11a/ground_truth_events.jsonl")
    return {row["clip_id"]: row for row in _read_jsonl(path) if row["event_type"] == "ABANDONED_OBJECT"}


def _audit_row(clip_id: str, mode: str):
    event = _gt_events()[clip_id]
    trace = _read_jsonl(Path("artifacts/phase11b1/traces-precheck") / f"{clip_id}.jsonl")
    rows = [row for row in trace if event["start_s"] - 2 <= row["time_s"] <= event["end_s"] + 2]
    rejected = [row for row in rows if row.get("owner_association_precheck_rejection_reason")]
    row = rejected[0] if rejected else rows[0]
    roi = CENTRAL_ROI if mode == "before" else None
    bbox = row["luggage_bbox"]
    center, bottom = bbox_points(bbox)
    inside = point_in_polygon(bottom, roi)
    return event, row, roi, bbox, center, bottom, inside


def _frame(clip_id: str, frame_id: int):
    capture = cv2.VideoCapture(str(Path("phase8_dataset/videos") / f"{clip_id}.mpg"))
    capture.set(cv2.CAP_PROP_POS_FRAMES, max(0, frame_id - 1))
    ok, image = capture.read()
    capture.release()
    if not ok:
        raise RuntimeError(f"failed to read {clip_id} frame {frame_id}")
    return image


def _draw(path: Path, image, clip_id, physical_id, roi, bbox, center, bottom, inside, mode):
    if roi:
        cv2.polylines(image, [__import__("numpy").array(roi, dtype="int32")], True, (0, 255, 255), 2)
    x1, y1, x2, y2 = map(int, bbox)
    cv2.rectangle(image, (x1, y1), (x2, y2), (255, 0, 255), 2)
    cv2.circle(image, tuple(map(int, center)), 4, (255, 255, 0), -1)
    cv2.circle(image, tuple(map(int, bottom)), 5, (0, 0, 255), -1)
    lines = [f"{clip_id} {physical_id} {mode}", f"frame={image.shape[1]}x{image.shape[0]} ROI=pixel",
             f"actual point=bottom-center {bottom[0]:.1f},{bottom[1]:.1f}", f"inside={inside}"]
    for index, text in enumerate(lines):
        cv2.putText(image, text, (8, 18 + index * 18), cv2.FONT_HERSHEY_SIMPLEX, .42, (255, 255, 255), 2)
        cv2.putText(image, text, (8, 18 + index * 18), cv2.FONT_HERSHEY_SIMPLEX, .42, (0, 0, 0), 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), image):
        raise RuntimeError(f"failed to write overlay: {path}")


def generate(mode: str):
    audit_rows = []
    for clip_id in CLIPS:
        event, trace, roi, bbox, center, bottom, inside = _audit_row(clip_id, mode)
        image = _frame(clip_id, trace["frame_id"])
        overlay = ROOT / "overlays" / f"{clip_id}-{mode}.png"
        _draw(overlay, image, clip_id, trace["physical_luggage_id"], roi, bbox, center, bottom, inside, mode)
        audit_rows.append({
            "clip_id": clip_id, "camera_id": clip_id, "frame_id": trace["frame_id"], "time_s": trace["time_s"],
            "original_width": image.shape[1], "original_height": image.shape[0],
            "detector_input_width": 640, "detector_input_height": 640, "letterbox_applied": False,
            "scale_x": 640 / image.shape[1], "scale_y": 640 / image.shape[0], "pad_x": 0, "pad_y": 0,
            "roi_id": "CENTRAL_ROI" if roi else "NONE", "roi_source_config": "scripts/phase11_infer.py",
            "roi_purpose": "intrusion/crowd central region" if roi else "abandoned config: no valid-floor restriction",
            "roi_coordinate_mode": "pixel", "roi_points_raw": roi, "roi_points_pixels": roi,
            "luggage_bbox_raw": bbox, "luggage_bbox_mode": "original_pixel_xyxy", "luggage_bbox_pixels": bbox,
            "center_x": center[0], "center_y": center[1], "bottom_center_x": bottom[0], "bottom_center_y": bottom[1],
            "inside_test_point_type": "bottom_center", "inside_test_point_x": bottom[0], "inside_test_point_y": bottom[1],
            "inside_result": inside, "root_cause_class": "BENCHMARK_POLICY_MISMATCH", "overlay_path": str(overlay),
            "notes": "OVERLAY_GENERATED_AGENT_INSPECTED_NOT_HUMAN_VERIFIED; direct resize, model postprocessor restores original pixels",
            "gt_event_id": event["event_id"],
        })
    ROOT.mkdir(parents=True, exist_ok=True)
    with (ROOT / f"roi-audit-{mode}.jsonl").open("w", encoding="utf-8") as handle:
        for row in audit_rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")
    return audit_rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("before", "after"), required=True)
    args = parser.parse_args()
    print(json.dumps(generate(args.mode), indent=2))
