from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import settings
from app.cv.contracts import read_events_jsonl, validate_event
from app.cv.detector import DEIMv2Detector
from app.cv.event_manager import CVEventManager
from app.cv.events.crowd_adapter import CrowdLifecycleAdapter
from app.cv.events.intrusion_adapter import IntrusionLifecycleAdapter
from app.cv.events.phase7c_abandoned_adapter import Phase7CAbandonedAdapter
from app.cv.worker import CVWorker
from app.publisher.jsonl_publisher import JsonlPublisher


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "artifacts" / "phase9-real-video"


@dataclass(frozen=True)
class Case:
    name: str
    video: Path
    camera_config: Path | None
    expected_type: str | None
    max_frames: int


CASES = (
    Case("aboda", ROOT / "datasets/aboda-video1.avi", None, "ABANDONED_OBJECT", 320),
    Case("intrusion", ROOT / "phase8_dataset/videos/Walk1.mpg",
         ROOT / "phase8_dataset/configs/CAM_WALK1.json", "ZONE_INTRUSION", 140),
    Case("crowd", ROOT / "phase8_dataset/videos/Meet_Crowd.mpg",
         ROOT / "phase8_dataset/configs/CAM_MEET_CROWD.json", "CROWD_THRESHOLD", 120),
    Case("negative", ROOT / "phase8_dataset/videos/Browse1.mpg",
         ROOT / "phase8_dataset/configs/CAM_BROWSE1.json", None, 220),
)


class CountingDetector:
    def __init__(self, detector: DEIMv2Detector):
        self.detector = detector
        self.calls = 0

    def detect(self, frame_data):
        self.calls += 1
        return self.detector.detect(frame_data)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_case_config(case: Case) -> tuple[str, dict[str, Any], list[Any], dict[str, Any]]:
    if case.camera_config is None:
        camera_id = "aboda-video1"
        phase7c = json.loads((ROOT / "configs/phase7c_cameras.example.json").read_text())
        abandoned = phase7c["cameras"]["aboda_camera_01"]
        rules = {
            "intrusion": {"dwell_seconds": 1.0},
            "crowd": {"count_threshold": 2, "hold_seconds": 1.0, "release_threshold": 1},
            "abandoned_object": {"phase7c": abandoned},
        }
        zones = [{"camera_id": camera_id, "zone_id": "OFFSCREEN",
                  "polygon": [[-10, -10], [-5, -10], [-5, -5], [-10, -5]], "enabled": True}]
        config = {"camera_id": camera_id, "source_type": "VIDEO",
                  "source_uri": str(case.video), "inference_fps": 5.0}
        return camera_id, config, zones, rules

    raw = json.loads(case.camera_config.read_text(encoding="utf-8"))
    camera_id = raw["camera_id"]
    intrusion = raw["intrusion"]
    crowd = raw["crowd"]
    abandoned = raw["abandoned"]
    rules = {
        "intrusion": {"dwell_seconds": intrusion["hold_s"]},
        "crowd": {"count_threshold": crowd["threshold"], "hold_seconds": crowd["hold_s"],
                  "release_threshold": max(0, crowd["threshold"] - 1)},
        "abandoned_object": {"phase7c": {
            "valid_floor_roi_polygon": abandoned.get("valid_floor_roi_polygon"),
            "stationary": {"hold_s": abandoned["stationary_hold_s"]},
            "owner": {"away_hold_s": abandoned["owner_away_hold_s"]},
        }},
    }
    zones = [{"camera_id": camera_id, "zone_id": intrusion["zone_id"],
              "polygon": intrusion["roi_polygon"], "enabled": True}]
    config = {"camera_id": camera_id, "source_type": "VIDEO",
              "source_uri": str(case.video), "inference_fps": 5.0}
    return camera_id, config, zones, rules


def _adapters(camera_id: str, raw_path: Path, rules: dict[str, Any], fps: float):
    raw = json.loads(raw_path.read_text(encoding="utf-8")) if raw_path else None
    intrusion_zones = ([{"camera_id": camera_id, "zone_id": raw["intrusion"]["zone_id"],
                         "polygon": raw["intrusion"]["roi_polygon"], "enabled": True}]
                       if raw else [])
    crowd_zones = ([{"camera_id": camera_id, "zone_id": raw["crowd"]["zone_id"],
                     "polygon": raw["crowd"]["roi_polygon"], "enabled": True}]
                   if raw else [])
    return (
        IntrusionLifecycleAdapter(camera_id, intrusion_zones, rules),
        CrowdLifecycleAdapter(camera_id, crowd_zones, rules),
        Phase7CAbandonedAdapter(camera_id, rules["abandoned_object"]["phase7c"], fps),
    )


def run_case(case: Case, detector: DEIMv2Detector, output_dir: Path) -> dict[str, Any]:
    if not case.video.is_file():
        raise FileNotFoundError(case.video)
    camera_id, camera_config, zones, rules = _load_case_config(case)
    output_path = output_dir / f"{case.name}.jsonl"
    output_path.unlink(missing_ok=True)
    counted = CountingDetector(detector)
    worker = CVWorker(
        camera_id, source_uri=str(case.video), detector=counted,
        publisher=JsonlPublisher(output_path), camera_config=camera_config,
        zones_config=zones, rules_config=rules,
        adapters=_adapters(camera_id, case.camera_config, rules, 5.0),
        event_manager=CVEventManager(camera_id),
    )
    events = worker.run(max_frames=case.max_frames)
    persisted = read_events_jsonl(output_path) if output_path.exists() else []
    for event in persisted:
        validate_event(event)
    serialized = [event.to_json() for event in persisted]
    duplicates = len(serialized) - len(set(serialized))
    sequences: dict[str, list[str]] = {}
    for event in persisted:
        sequences.setdefault(event.event_id, []).append(event.event_state)
    lifecycle_valid = all(
        states[0] == "START"
        and states[-1] == "END"
        and all(state == "UPDATE" for state in states[1:-1])
        for states in sequences.values()
    )
    types = sorted({event.event_type for event in persisted})
    expected_seen = case.expected_type is None or case.expected_type in types
    return {
        "case": case.name, "video": str(case.video.relative_to(ROOT)),
        "sha256": _sha256(case.video), "processed_frames": worker.processed_frames,
        "detector_calls": counted.calls, "track_store_tracks": len(worker.track_store.tracks),
        "events": len(events), "persisted_events": len(persisted), "event_types": types,
        "duplicate_lifecycle_records": duplicates, "lifecycle_valid": lifecycle_valid,
        "expected_event_seen": expected_seen,
        "one_inference_per_frame": counted.calls == worker.processed_frames,
        "jsonl": str(output_path.relative_to(ROOT)),
        "pass": (counted.calls == worker.processed_frames and duplicates == 0
                 and lifecycle_valid and expected_seen),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 9 production real-video regression")
    parser.add_argument("--case", action="append", choices=[case.name for case in CASES])
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    selected = [case for case in CASES if not args.case or case.name in args.case]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    detector = DEIMv2Detector(**settings.detector_config)
    results = [run_case(case, detector, args.output_dir) for case in selected]
    report = {"schema": "phase9-real-video-v1", "results": results,
              "pass": all(result["pass"] for result in results)}
    report_path = args.output_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
