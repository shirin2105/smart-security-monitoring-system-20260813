
from app.common.schemas import DetectionResult, FrameData, TrackResult

try:
    import ultralytics  # noqa: F401  (availability flag for optional integration)

    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False


def compute_iou(box1: list[float], box2: list[float]) -> float:
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
    def __init__(self, camera_id: str, max_missed_frames: int = 10):
        self.camera_id = camera_id
        self.next_track_id: int = 1
        self.active_tracks: dict[int, list[float]] = {}  # track_id -> bbox
        self.track_first_seen: dict[int, str] = {}
        self.max_missed_frames = max_missed_frames
        self._missed_frames: dict[int, int] = {}

    def track(self, detections: list[DetectionResult], frame_data: FrameData) -> list[TrackResult]:
        timestamp = frame_data.captured_at
        results: list[TrackResult] = []
        updated_tracks: dict[int, list[float]] = {}

        for det in detections:
            best_iou = 0.0
            best_id = None

            # Simple IOU matching against tracks seen in previous frames
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

        # Track IDs persist across frames: tracks not matched this frame are
        # kept so the same object keeps its ID (dwell/temporal state depends
        # on stable IDs). Stale tracks are dropped after MAX_MISSED_FRAMES.
        for track_id, last_bbox in self.active_tracks.items():
            if track_id not in updated_tracks:
                missed = self._missed_frames.get(track_id, 0) + 1
                if missed <= self.max_missed_frames:
                    self._missed_frames[track_id] = missed
                    updated_tracks[track_id] = last_bbox

        # Clear missed counters for tracks matched this frame
        for track_id in updated_tracks:
            self._missed_frames.pop(track_id, None)

        self.active_tracks = updated_tracks
        return results
