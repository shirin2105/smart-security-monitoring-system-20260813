from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.evaluation.phase8_caviar import camera_config, derive_events, parse_observations
from app.evaluation.phase8_config import validate_camera_config, validate_manifest
from app.evaluation.phase8_schema import ground_truth_from_mapping

SOURCE_URL = "https://groups.inf.ed.ac.uk/vision/DATASETS/CAVIAR/CAVIARDATA1/"


def video_metadata(path: Path) -> tuple[float, int, int, float]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"Unreadable video: {path}")
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frames = 0
    while capture.grab():
        frames += 1
    capture.release()
    if fps <= 0 or frames <= 0 or width <= 0 or height <= 0:
        raise RuntimeError(f"Invalid video metadata: {path}")
    return fps, width, height, frames / fps


def prepare(output: Path) -> None:
    catalog = json.loads((ROOT / "tools/phase8/caviar_catalog.json").read_text())
    config_dir = output / "configs"
    config_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"version": 1, "source": SOURCE_URL, "clips": []}
    inventory: list[dict] = []
    all_events: list[dict] = []
    for item in catalog:
        clip_id = item["clip_id"]
        camera_id = f"CAM_{clip_id.upper()}"
        video = output / "videos" / Path(item["video"]).name
        xml = output / "source_xml" / f"{clip_id}.xml"
        fps, width, height, duration = video_metadata(video)
        observations, xml_frames = parse_observations(xml)
        dataset_name = item.get("dataset", "CAVIARDATA1")
        item_source = f"https://groups.inf.ed.ac.uk/vision/DATASETS/CAVIAR/{dataset_name}/{item['video']}"
        config = camera_config(camera_id, item["event_target"])
        events = derive_events(clip_id, camera_id, observations, fps,
                               config["intrusion"]["roi_polygon"],
                               config["crowd"]["roi_polygon"])
        all_events.extend(events)
        present = {event["event_type"] for event in events}
        tags = []
        for event_type, slug in (("ZONE_INTRUSION", "intrusion"),
                                 ("CROWD_THRESHOLD", "crowd"),
                                 ("ABANDONED_OBJECT", "abandoned")):
            tags.append(f"{slug}_{'positive' if event_type in present else 'negative'}")
        validate_camera_config(config, camera_id)
        config_name = f"{camera_id}.json"
        (config_dir / config_name).write_text(json.dumps(config, indent=2), encoding="utf-8")
        manifest["clips"].append({
            "clip_id": clip_id, "video_path": f"videos/{video.name}",
            "camera_id": camera_id, "camera_config_path": f"configs/{config_name}",
            "scenario_tags": tags + [item["event_target"].lower()],
            "expected_duration_s": round(duration, 6),
        })
        inventory.append({
            "clip_id": clip_id, "original_filename": video.name,
            "event_target": item["event_target"], "positive_negative": item["polarity"],
            "source": item_source, "duration_s": round(duration, 6), "fps": fps,
            "width": width, "height": height,
            "notes": f"Original MPEG; XML frames={xml_frames}; events={len(events)}",
        })
    validate_manifest(manifest)
    for event in all_events:
        ground_truth_from_mapping(event)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with (output / "ground_truth_events.jsonl").open("w", encoding="utf-8") as handle:
        for event in all_events:
            handle.write(json.dumps(event) + "\n")
    with (output / "dataset_inventory.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(inventory[0]))
        writer.writeheader()
        writer.writerows(inventory)
    print(json.dumps({"clips": len(catalog), "events": len(all_events),
                      "duration_s": round(sum(row["duration_s"] for row in inventory), 3)}, indent=2))


if __name__ == "__main__":
    prepare(ROOT / "phase8_dataset")
