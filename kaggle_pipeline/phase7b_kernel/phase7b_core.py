from __future__ import annotations
from dataclasses import dataclass, field
from collections import defaultdict
from typing import Dict, List, Sequence, Tuple
import json
from pathlib import Path
import numpy as np

CLASS_NAMES = {0: "person", 1: "backpack", 2: "handbag", 3: "suitcase"}
ID_NAMESPACE = 1_000_000

@dataclass
class TrackerConfig:
    detector_low_threshold: float = 0.05
    track_activation_threshold: float = 0.25
    high_conf_det_threshold: float = 0.25
    minimum_consecutive_frames: int = 2
    minimum_iou_threshold: float = 0.10
    lost_track_buffer: int = 30

@dataclass
class TrackObservation:
    frame_index: int
    timestamp_s: float
    class_id: int
    class_name: str
    global_track_id: int
    local_track_id: int
    bbox_xyxy: Tuple[float, float, float, float]
    confidence: float

    @property
    def center(self):
        x1, y1, x2, y2 = self.bbox_xyxy
        return ((x1+x2)/2.0, (y1+y2)/2.0)

@dataclass
class TrackRecord:
    class_id: int
    global_track_id: int
    first_frame: int
    last_frame: int
    first_timestamp_s: float
    last_timestamp_s: float
    observations: int = 0
    confidence_sum: float = 0.0
    centers: List[Tuple[float, float]] = field(default_factory=list)

    def update(self, obs: TrackObservation):
        self.last_frame = obs.frame_index
        self.last_timestamp_s = obs.timestamp_s
        self.observations += 1
        self.confidence_sum += float(obs.confidence)
        self.centers.append(obs.center)

    @property
    def duration_s(self):
        return max(0.0, self.last_timestamp_s - self.first_timestamp_s)

    @property
    def mean_confidence(self):
        return self.confidence_sum / max(1, self.observations)

class ClasswiseByteTrack:
    """Separate ByteTrack instance per semantic class."""
    def __init__(self, frame_rate: float, config: TrackerConfig | None = None):
        self.config = config or TrackerConfig()
        import supervision as sv
        from trackers import ByteTrackTracker
        self._sv = sv
        self._trackers = {
            cid: ByteTrackTracker(
                lost_track_buffer=self.config.lost_track_buffer,
                frame_rate=max(float(frame_rate), 1e-6),
                track_activation_threshold=self.config.track_activation_threshold,
                minimum_consecutive_frames=self.config.minimum_consecutive_frames,
                minimum_iou_threshold=self.config.minimum_iou_threshold,
                high_conf_det_threshold=self.config.high_conf_det_threshold,
            )
            for cid in CLASS_NAMES
        }

    def reset(self):
        for tracker in self._trackers.values():
            tracker.reset()

    def update(self, xyxy, confidence, class_id, frame_index: int, timestamp_s: float):
        xyxy = np.asarray(xyxy, dtype=np.float32).reshape(-1, 4)
        confidence = np.asarray(confidence, dtype=np.float32).reshape(-1)
        class_id = np.asarray(class_id, dtype=np.int32).reshape(-1)
        if not (len(xyxy) == len(confidence) == len(class_id)):
            raise ValueError("xyxy/confidence/class_id length mismatch")

        keep = (confidence >= self.config.detector_low_threshold) & np.isin(class_id, list(CLASS_NAMES))
        xyxy, confidence, class_id = xyxy[keep], confidence[keep], class_id[keep]
        output = []

        for cid, tracker in self._trackers.items():
            mask = class_id == cid
            if mask.any():
                det = self._sv.Detections(
                    xyxy=xyxy[mask],
                    confidence=confidence[mask],
                    class_id=class_id[mask],
                )
            else:
                det = self._sv.Detections.empty()

            # `trackers` exposes a shared update(detections, frame=None) contract.
            # Video time remains attached to our observation; ByteTrack advances per call.
            tracked = tracker.update(det)
            if tracked.tracker_id is None:
                continue

            for box, score, ret_cid, local_tid in zip(
                tracked.xyxy, tracked.confidence, tracked.class_id, tracked.tracker_id
            ):
                local_tid = int(local_tid)
                if local_tid < 0:
                    continue
                ret_cid = int(ret_cid)
                if ret_cid != cid:
                    raise RuntimeError(f"Class contamination tracker={cid} output={ret_cid}")
                output.append(TrackObservation(
                    frame_index=int(frame_index),
                    timestamp_s=float(timestamp_s),
                    class_id=cid,
                    class_name=CLASS_NAMES[cid],
                    global_track_id=(cid + 1) * ID_NAMESPACE + local_tid,
                    local_track_id=local_tid,
                    bbox_xyxy=tuple(float(v) for v in box),
                    confidence=float(score),
                ))
        return sorted(output, key=lambda x: (x.class_id, x.global_track_id))

class TrackHistory:
    def __init__(self):
        self.records: Dict[int, TrackRecord] = {}
        self.confirmed_observations = 0

    def update(self, observations: Sequence[TrackObservation]):
        self.confirmed_observations += len(observations)
        for obs in observations:
            rec = self.records.get(obs.global_track_id)
            if rec is None:
                rec = TrackRecord(
                    class_id=obs.class_id,
                    global_track_id=obs.global_track_id,
                    first_frame=obs.frame_index,
                    last_frame=obs.frame_index,
                    first_timestamp_s=obs.timestamp_s,
                    last_timestamp_s=obs.timestamp_s,
                )
                self.records[obs.global_track_id] = rec
            rec.update(obs)

    def summary(self):
        by_class = defaultdict(list)
        for rec in self.records.values():
            by_class[CLASS_NAMES[rec.class_id]].append(rec)
        out = {"total_tracks": len(self.records), "confirmed_observations": self.confirmed_observations, "by_class": {}}
        for name in CLASS_NAMES.values():
            items = by_class.get(name, [])
            durations = [r.duration_s for r in items]
            obs_counts = [r.observations for r in items]
            out["by_class"][name] = {
                "tracks": len(items),
                "mean_duration_s": float(np.mean(durations)) if durations else 0.0,
                "median_duration_s": float(np.median(durations)) if durations else 0.0,
                "max_duration_s": float(np.max(durations)) if durations else 0.0,
                "mean_observations": float(np.mean(obs_counts)) if obs_counts else 0.0,
                "short_track_ratio_lt_1s": float(np.mean([d < 1.0 for d in durations])) if durations else 0.0,
                "mean_track_confidence": float(np.mean([r.mean_confidence for r in items])) if items else 0.0,
            }
        return out

def append_jsonl(path, observations):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for obs in observations:
            row = {
                "frame_index": obs.frame_index,
                "timestamp_s": obs.timestamp_s,
                "class_id": obs.class_id,
                "class_name": obs.class_name,
                "global_track_id": obs.global_track_id,
                "local_track_id": obs.local_track_id,
                "bbox_xyxy": list(obs.bbox_xyxy),
                "confidence": obs.confidence,
                "center_xy": list(obs.center),
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

def draw_tracks(frame_bgr, observations, trails, max_trail_points=30):
    import cv2
    out = frame_bgr.copy()
    colors = {0:(0,220,0), 1:(255,180,0), 2:(255,0,220), 3:(0,180,255)}
    for obs in observations:
        x1,y1,x2,y2 = map(int, obs.bbox_xyxy)
        color = colors.get(obs.class_id, (255,255,255))
        label = f"{obs.class_name} ID={obs.global_track_id} {obs.confidence:.2f}"
        cv2.rectangle(out, (x1,y1), (x2,y2), color, 2)
        cv2.putText(out, label, (x1,max(18,y1-7)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
        cx,cy = map(int, obs.center)
        trail = trails.setdefault(obs.global_track_id, [])
        trail.append((cx,cy))
        if len(trail) > max_trail_points:
            del trail[:-max_trail_points]
        if len(trail) >= 2:
            pts = np.asarray(trail, dtype=np.int32).reshape(-1,1,2)
            cv2.polylines(out, [pts], False, color, 2)
    return out
