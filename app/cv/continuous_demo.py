"""Continuously replay one clip through a single resident DEIMv2 model."""
from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import cv2

from app.config import settings
from app.cv.detector import DEIMv2Detector
from app.cv.tracker import ByteTrackMultiObjectTracker
from app.cv.worker import CVWorker


class PreviewDetector:
    """Decorate the resident detector and atomically publish its latest frame."""

    def __init__(self, detector: DEIMv2Detector, preview_path: Path):
        self.detector = detector
        self.preview_path = preview_path
        preview_path.parent.mkdir(parents=True, exist_ok=True)

    def detect(self, frame_data):
        detections, latency_ms = self.detector.detect(frame_data)
        image = frame_data.image.copy()
        for detection in detections:
            x1, y1, x2, y2 = (int(value) for value in detection.bbox)
            color = (40, 220, 40) if detection.class_name == "person" else (40, 170, 255)
            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
            label = f"{detection.class_name} {detection.confidence:.2f}"
            cv2.putText(image, label, (x1, max(18, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, color, 2, cv2.LINE_AA)
        temporary = self.preview_path.with_suffix(".tmp.jpg")
        if not cv2.imwrite(str(temporary), image):
            raise RuntimeError("failed to write annotated preview")
        os.replace(temporary, self.preview_path)
        return detections, latency_ms


def run_forever(clip: str, camera_id: str, frames: int, interval: float, preview: Path) -> None:
    detector = PreviewDetector(DEIMv2Detector(**settings.detector_config), preview)
    print("[cv-loop] DEIMv2 loaded once; continuous replay started", flush=True)
    while True:
        tracker = ByteTrackMultiObjectTracker(
            camera_id=camera_id,
            frame_rate=5.0,
            track_activation_threshold=0.05,
            high_conf_det_threshold=0.05,
            minimum_consecutive_frames=1,
        )
        worker = CVWorker(
            camera_id=camera_id,
            source_uri=clip,
            detector=detector,
            tracker=tracker,
        )
        candidates = worker.run(max_frames=frames)
        print(f"[cv-loop] completed replay events={len(candidates)}", flush=True)
        time.sleep(max(0.0, interval))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clip", default="tests/clips/walking_people.mp4")
    parser.add_argument("--camera", default="cam_01")
    parser.add_argument("--frames", type=int, default=3)
    parser.add_argument("--interval", type=float, default=3.0)
    parser.add_argument("--preview", type=Path, default=Path(".qa-tmp/camera-1-latest.jpg"))
    args = parser.parse_args()
    run_forever(args.clip, args.camera, max(1, args.frames), args.interval, args.preview)


if __name__ == "__main__":
    main()
