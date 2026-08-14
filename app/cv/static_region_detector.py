from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from app.common.schemas import StaticRegionObservation
from app.common.time_utils import calculate_duration_seconds


@dataclass
class _RegionState:
    region_id: str
    bbox: List[float]
    first_seen_at: str
    last_seen_at: str


def _iou(a: List[float], b: List[float]) -> float:
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - intersection
    return intersection / union if union > 0 else 0.0


class StaticRegionDetector:
    """Detect persistent introduced foreground in a fixed-camera stream."""

    def __init__(self, camera_id: str, config: Optional[dict] = None):
        cfg = config or {}
        self.camera_id = camera_id
        self.warmup_seconds = float(cfg.get("warmup_seconds", 2.0))
        self.stationary_seconds = float(cfg.get("stationary_seconds", 15.0))
        self.clear_grace_seconds = float(cfg.get("clear_grace_seconds", 2.0))
        self.min_area_ratio = float(cfg.get("min_area_ratio", 0.001))
        self.max_area_ratio = float(cfg.get("max_area_ratio", 0.25))
        self.threshold = int(cfg.get("foreground_threshold", 25))
        self.kernel_size = max(1, int(cfg.get("morphology_kernel", 3)))
        self.match_iou = float(cfg.get("match_iou", 0.25))
        self.learning_rate = float(cfg.get("learning_rate", 0.05))
        self.reset()

    def reset(self) -> None:
        self._baseline: Optional[np.ndarray] = None
        self._started_at: Optional[str] = None
        self._regions: Dict[str, _RegionState] = {}
        self._next_id = 1

    def _boxes(self, gray: np.ndarray) -> List[List[float]]:
        delta = cv2.absdiff(cv2.convertScaleAbs(gray), cv2.convertScaleAbs(self._baseline))
        mask = cv2.threshold(delta, self.threshold, 255, cv2.THRESH_BINARY)[1]
        kernel = np.ones((self.kernel_size, self.kernel_size), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        area = gray.shape[0] * gray.shape[1]
        boxes = []
        for contour in cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
            x, y, w, h = cv2.boundingRect(contour)
            ratio = (w * h) / area
            if self.min_area_ratio <= ratio <= self.max_area_ratio:
                boxes.append([float(x), float(y), float(x + w), float(y + h)])
        return boxes

    def update(self, frame: np.ndarray, captured_at: str) -> List[StaticRegionObservation]:
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return []
        gray = cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (5, 5), 0).astype(np.float32)
        if self._baseline is None:
            self._baseline, self._started_at = gray, captured_at
            return []
        if calculate_duration_seconds(self._started_at, captured_at) < self.warmup_seconds:
            cv2.accumulateWeighted(gray, self._baseline, self.learning_rate)
            return []

        boxes, matched = self._boxes(gray), set()
        for box in boxes:
            best = max(self._regions.values(), key=lambda r: _iou(box, r.bbox), default=None)
            if best is None or _iou(box, best.bbox) < self.match_iou or best.region_id in matched:
                best = _RegionState(f"{self.camera_id}-region-{self._next_id}", box, captured_at, captured_at)
                self._next_id += 1
                self._regions[best.region_id] = best
            else:
                best.bbox, best.last_seen_at = box, captured_at
            matched.add(best.region_id)

        for region_id, region in list(self._regions.items()):
            if region_id not in matched and calculate_duration_seconds(region.last_seen_at, captured_at) >= self.clear_grace_seconds:
                del self._regions[region_id]

        observations = []
        for region_id in matched:
            region = self._regions[region_id]
            persistence = calculate_duration_seconds(region.first_seen_at, captured_at)
            if persistence >= self.stationary_seconds:
                observations.append(StaticRegionObservation(
                    region_id=region.region_id, bbox=region.bbox,
                    first_seen_at=region.first_seen_at, last_seen_at=captured_at,
                    persistence_seconds=persistence, confidence=min(0.99, 0.5 + persistence / max(1.0, self.stationary_seconds) * 0.25),
                ))
        return observations
