from typing import List, Dict
from app.common.schemas import DetectionResult, TrackResult, FrameData

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False


def compute_iou(box1: List[float], box2: List[float]) -> float:
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])

    union = area1 + area2 - intersection
    if union <= 0:
        return 0.0
    return intersection / union


class MultiObjectTracker:
    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        self.next_track_id: int = 1
        self.active_tracks: Dict[int, List[float]] = {}  # track_id -> bbox
        self.track_first_seen: Dict[int, str] = {}

    def track(self, detections: List[DetectionResult], frame_data: FrameData) -> List[TrackResult]:
        timestamp = frame_data.captured_at
        results: List[TrackResult] = []
        updated_tracks: Dict[int, List[float]] = {}

        for det in detections:
            best_iou = 0.0
            best_id = None

            # Simple IOU matching across consecutive frames
            for track_id, last_bbox in self.active_tracks.items():
                iou = compute_iou(det.bbox, last_bbox)
                if iou > 0.3 and iou > best_iou:
                    best_iou = iou
                    best_id = track_id

            if best_id is None:
                assigned_id = self.next_track_id
                self.next_track_id += 1
                self.track_first_seen[assigned_id] = timestamp
            else:
                assigned_id = best_id

            updated_tracks[assigned_id] = det.bbox

            results.append(
                TrackResult(
                    track_id=assigned_id,
                    class_name=det.class_name,
                    bbox=det.bbox,
                    confidence=det.confidence,
                    first_seen_at=self.track_first_seen.get(assigned_id, timestamp),
                    last_seen_at=timestamp,
                )
            )

        self.active_tracks = updated_tracks
        return results
