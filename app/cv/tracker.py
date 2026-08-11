from __future__ import annotations

from typing import Any, Callable
import zlib

import numpy as np

from app.common.schemas import DetectionResult, FrameData, TrackResult

ID_NAMESPACE = 100_000
CLASS_IDS = {"person": 0, "luggage": 1}


def _default_tracker_factory(frame_rate: float, **config):
    from trackers import ByteTrackTracker

    return ByteTrackTracker(frame_rate=max(float(frame_rate), 1e-6), **config)


def _detections(xyxy, confidence, class_id):
    import supervision as sv

    if len(xyxy) == 0:
        return sv.Detections.empty()
    return sv.Detections(xyxy=xyxy, confidence=confidence, class_id=class_id)


class ByteTrackMultiObjectTracker:
    """Camera-local ByteTrack state with strict class isolation."""

    def __init__(self, camera_id: str, frame_rate: float = 5.0,
                 tracker_factory: Callable[..., Any] | None = None,
                 detections_factory: Callable[..., Any] | None = None,
                 **config):
        self.camera_id = camera_id
        self._camera_namespace = zlib.crc32(camera_id.encode("utf-8"))
        factory = tracker_factory or _default_tracker_factory
        defaults = {
            "lost_track_buffer": 30,
            "track_activation_threshold": 0.25,
            "minimum_consecutive_frames": 2,
            "minimum_iou_threshold": 0.10,
            "high_conf_det_threshold": 0.60,
        }
        defaults.update(config)
        self._lost_track_buffer = max(0, int(defaults["lost_track_buffer"]))
        self._trackers = {cid: factory(frame_rate, **defaults) for cid in CLASS_IDS.values()}
        self._make_detections = detections_factory or _detections
        self._first_seen: dict[int, str] = {}
        self._last_returned_frame: dict[int, int] = {}
        self._frame_index = 0

    def track(self, detections: list[DetectionResult], frame_data: FrameData) -> list[TrackResult]:
        self._frame_index += 1
        for detection in detections:
            self._validate(detection)
        results = []
        for name, cid in CLASS_IDS.items():
            selected = [d for d in detections if d.class_name == name]
            xyxy = np.asarray([d.bbox for d in selected], dtype=np.float32).reshape(-1, 4)
            scores = np.asarray([d.confidence for d in selected], dtype=np.float32)
            class_ids = np.full(len(selected), cid, dtype=np.int32)
            tracked = self._trackers[cid].update(self._make_detections(xyxy, scores, class_ids))
            if getattr(tracked, "tracker_id", None) is None:
                continue
            for box, score, returned_cid, local_id in zip(
                    tracked.xyxy, tracked.confidence, tracked.class_id, tracked.tracker_id):
                if int(returned_cid) != cid:
                    raise RuntimeError(f"class contamination: tracker={cid}, output={returned_cid}")
                if int(local_id) < 0:
                    continue
                if int(local_id) >= ID_NAMESPACE:
                    raise RuntimeError("local tracker ID exhausted its public namespace")
                global_id = (self._camera_namespace * 2 + cid) * ID_NAMESPACE + int(local_id)
                first_seen = self._first_seen.setdefault(global_id, frame_data.captured_at)
                self._last_returned_frame[global_id] = self._frame_index
                results.append(TrackResult(track_id=global_id, class_name=name,
                                           bbox=[float(v) for v in box], confidence=float(score),
                                           first_seen_at=first_seen,
                                           last_seen_at=frame_data.captured_at))
        # ByteTrack may revive a lost ID for lost_track_buffer updates. Expire
        # metadata only after that continuity window has elapsed.
        expired = [track_id for track_id, last_frame in self._last_returned_frame.items()
                   if self._frame_index - last_frame > self._lost_track_buffer]
        for track_id in expired:
            self._last_returned_frame.pop(track_id, None)
            self._first_seen.pop(track_id, None)
        return sorted(results, key=lambda item: item.track_id)

    @staticmethod
    def _validate(detection: DetectionResult):
        if detection.class_name not in CLASS_IDS:
            raise ValueError(f"unsupported detection class: {detection.class_name}")
        box = np.asarray(detection.bbox, dtype=float)
        if box.shape != (4,) or not np.isfinite(box).all() or box[2] <= box[0] or box[3] <= box[1]:
            raise ValueError("detection bbox must be finite ordered xyxy")
        if not np.isfinite(detection.confidence) or not 0 <= detection.confidence <= 1:
            raise ValueError("detection confidence must be finite within [0, 1]")
