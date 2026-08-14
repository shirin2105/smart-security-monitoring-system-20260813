from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict
from typing import Dict, List, Sequence, Tuple
import json
from pathlib import Path
import numpy as np

RUNTIME_CLASS_NAMES = {0: "person", 1: "luggage"}
ID_NAMESPACE = 1_000_000


def bbox_iou(a, b) -> float:
    ax1, ay1, ax2, ay2 = map(float, a)
    bx1, by1, bx2, by2 = map(float, b)
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    aa = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    ba = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = aa + ba - inter
    return inter / union if union > 0 else 0.0


@dataclass
class TrackerConfig:
    detector_low_threshold: float = 0.05
    track_activation_threshold: float = 0.25
    high_conf_det_threshold: float = 0.60
    minimum_consecutive_frames: int = 2
    minimum_iou_threshold: float = 0.10
    lost_track_buffer: int = 30


@dataclass
class QualityConfig:
    # Provisional "eligible for event logic" gate, NOT final abandoned thresholds.
    person_min_age_s: float = 0.7
    person_min_hits: int = 3
    person_high_conf_threshold: float = 0.40
    person_min_high_hits: int = 2

    luggage_min_age_s: float = 1.5
    luggage_min_hits: int = 5
    luggage_high_conf_threshold: float = 0.35
    luggage_min_high_hits: int = 3


@dataclass
class BackgroundConfig:
    warmup_s: float = 8.0
    max_first_seen_s: float = 1.0
    min_duration_s: float = 3.0
    min_hits: int = 20
    max_stationary_norm: float = 0.25
    suppress_iou: float = 0.50


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
    def center(self) -> Tuple[float, float]:
        x1, y1, x2, y2 = self.bbox_xyxy
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


@dataclass
class TrackState:
    class_id: int
    global_track_id: int
    first_seen_s: float
    last_seen_s: float
    first_frame: int
    last_frame: int
    hits: int = 0
    high_conf_hits: int = 0
    max_confidence: float = 0.0
    confidence_sum: float = 0.0
    boxes: List[Tuple[float, float, float, float]] = field(default_factory=list)
    centers: List[Tuple[float, float]] = field(default_factory=list)

    @property
    def age_s(self) -> float:
        return max(0.0, self.last_seen_s - self.first_seen_s)

    @property
    def mean_confidence(self) -> float:
        return self.confidence_sum / max(self.hits, 1)

    @property
    def median_bbox(self) -> Tuple[float, float, float, float]:
        if not self.boxes:
            return (0.0, 0.0, 0.0, 0.0)
        arr = np.asarray(self.boxes, dtype=np.float32)
        return tuple(float(v) for v in np.median(arr, axis=0))

    @property
    def stationary_norm(self) -> float:
        """Robust bbox-jitter-normalized spread; lower means more stationary."""
        if len(self.centers) < 3 or not self.boxes:
            return float("inf")
        centers = np.asarray(self.centers, dtype=np.float32)
        med = np.median(centers, axis=0)
        dist = np.linalg.norm(centers - med, axis=1)
        robust_disp = float(np.percentile(dist, 90))
        boxes = np.asarray(self.boxes, dtype=np.float32)
        w = np.maximum(1.0, boxes[:, 2] - boxes[:, 0])
        h = np.maximum(1.0, boxes[:, 3] - boxes[:, 1])
        diag = float(np.median(np.sqrt(w * w + h * h)))
        return robust_disp / max(diag, 1.0)


@dataclass
class BackgroundAnchor:
    class_id: int
    bbox_xyxy: Tuple[float, float, float, float]
    source_track_id: int
    stationary_norm: float


class RuntimeByteTrack:
    """
    Two trackers only:
      0 = person
      1 = generic luggage
    """
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
            for cid in RUNTIME_CLASS_NAMES
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

        keep = (
            (confidence >= self.config.detector_low_threshold)
            & np.isin(class_id, list(RUNTIME_CLASS_NAMES))
        )
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

            tracked = tracker.update(det)
            if tracked.tracker_id is None:
                continue

            for box, score, returned_cid, local_tid in zip(
                tracked.xyxy,
                tracked.confidence,
                tracked.class_id,
                tracked.tracker_id,
            ):
                local_tid = int(local_tid)
                if local_tid < 0:
                    continue
                returned_cid = int(returned_cid)
                if returned_cid != cid:
                    raise RuntimeError(
                        f"Runtime class contamination: tracker={cid}, output={returned_cid}"
                    )
                output.append(
                    TrackObservation(
                        frame_index=int(frame_index),
                        timestamp_s=float(timestamp_s),
                        class_id=cid,
                        class_name=RUNTIME_CLASS_NAMES[cid],
                        global_track_id=(cid + 1) * ID_NAMESPACE + local_tid,
                        local_track_id=local_tid,
                        bbox_xyxy=tuple(float(v) for v in box),
                        confidence=float(score),
                    )
                )
        return sorted(output, key=lambda o: (o.class_id, o.global_track_id))


class CandidateManager:
    def __init__(
        self,
        quality: QualityConfig | None = None,
        background: BackgroundConfig | None = None,
    ):
        self.quality = quality or QualityConfig()
        self.background = background or BackgroundConfig()
        self.states: Dict[int, TrackState] = {}
        self.anchors: List[BackgroundAnchor] = []
        self.background_track_ids = set()
        self.warmup_finalized = False

    def _high_threshold(self, class_id: int) -> float:
        if class_id == 0:
            return self.quality.person_high_conf_threshold
        return self.quality.luggage_high_conf_threshold

    def update_state(self, obs: TrackObservation) -> TrackState:
        state = self.states.get(obs.global_track_id)
        if state is None:
            state = TrackState(
                class_id=obs.class_id,
                global_track_id=obs.global_track_id,
                first_seen_s=obs.timestamp_s,
                last_seen_s=obs.timestamp_s,
                first_frame=obs.frame_index,
                last_frame=obs.frame_index,
            )
            self.states[obs.global_track_id] = state

        state.last_seen_s = obs.timestamp_s
        state.last_frame = obs.frame_index
        state.hits += 1
        state.confidence_sum += float(obs.confidence)
        state.max_confidence = max(state.max_confidence, float(obs.confidence))
        if obs.confidence >= self._high_threshold(obs.class_id):
            state.high_conf_hits += 1
        state.boxes.append(obs.bbox_xyxy)
        state.centers.append(obs.center)
        return state

    def finalize_warmup(self):
        if self.warmup_finalized:
            return

        anchors = []
        for state in self.states.values():
            if state.first_seen_s > self.background.max_first_seen_s:
                continue
            if state.age_s < self.background.min_duration_s:
                continue
            if state.hits < self.background.min_hits:
                continue
            s_norm = state.stationary_norm
            if not np.isfinite(s_norm) or s_norm > self.background.max_stationary_norm:
                continue

            anchor = BackgroundAnchor(
                class_id=state.class_id,
                bbox_xyxy=state.median_bbox,
                source_track_id=state.global_track_id,
                stationary_norm=float(s_norm),
            )
            anchors.append(anchor)
            self.background_track_ids.add(state.global_track_id)

        self.anchors = anchors
        self.warmup_finalized = True

    def background_match(self, obs: TrackObservation):
        if obs.global_track_id in self.background_track_ids:
            return True, 1.0, obs.global_track_id

        best_iou = 0.0
        best_source = None
        for anchor in self.anchors:
            if anchor.class_id != obs.class_id:
                continue
            iou = bbox_iou(obs.bbox_xyxy, anchor.bbox_xyxy)
            if iou > best_iou:
                best_iou = iou
                best_source = anchor.source_track_id

        return (
            best_iou >= self.background.suppress_iou,
            float(best_iou),
            best_source,
        )

    def eligible(self, state: TrackState, is_background: bool) -> bool:
        if is_background:
            return False

        if state.class_id == 0:
            return (
                state.age_s >= self.quality.person_min_age_s
                and state.hits >= self.quality.person_min_hits
                and state.high_conf_hits >= self.quality.person_min_high_hits
            )

        return (
            state.age_s >= self.quality.luggage_min_age_s
            and state.hits >= self.quality.luggage_min_hits
            and state.high_conf_hits >= self.quality.luggage_min_high_hits
        )

    def process(
        self,
        observations: Sequence[TrackObservation],
        timestamp_s: float,
    ):
        for obs in observations:
            self.update_state(obs)

        if (
            not self.warmup_finalized
            and timestamp_s >= self.background.warmup_s
        ):
            self.finalize_warmup()

        enriched = []
        for obs in observations:
            state = self.states[obs.global_track_id]
            is_bg, bg_iou, bg_source = self.background_match(obs)
            is_eligible = self.eligible(state, is_bg)
            if not self.warmup_finalized:
                is_eligible = False
            status = "BACKGROUND" if is_bg else ("ELIGIBLE" if is_eligible else "TRACK_ONLY")
            enriched.append({
                "observation": obs,
                "status": status,
                "is_background": bool(is_bg),
                "background_iou": float(bg_iou),
                "background_source_track_id": bg_source,
                "eligible": bool(is_eligible),
                "age_s": float(state.age_s),
                "hits": int(state.hits),
                "high_conf_hits": int(state.high_conf_hits),
                "max_confidence": float(state.max_confidence),
                "mean_confidence": float(state.mean_confidence),
            })
        return enriched

    def summary(self):
        by_class = defaultdict(list)
        for state in self.states.values():
            by_class[RUNTIME_CLASS_NAMES[state.class_id]].append(state)

        out = {
            "total_tracks": len(self.states),
            "background_anchor_count": len(self.anchors),
            "background_track_ids": len(self.background_track_ids),
            "by_class": {},
        }
        for name in RUNTIME_CLASS_NAMES.values():
            items = by_class.get(name, [])
            ages = [s.age_s for s in items]
            out["by_class"][name] = {
                "tracks": len(items),
                "mean_duration_s": float(np.mean(ages)) if ages else 0.0,
                "median_duration_s": float(np.median(ages)) if ages else 0.0,
                "max_duration_s": float(np.max(ages)) if ages else 0.0,
                "short_track_ratio_lt_1s": (
                    float(np.mean([a < 1.0 for a in ages])) if ages else 0.0
                ),
                "mean_track_confidence": (
                    float(np.mean([s.mean_confidence for s in items])) if items else 0.0
                ),
            }
        return out


def write_enriched_jsonl(path, enriched_rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in enriched_rows:
            obs = row["observation"]
            payload = {
                "frame_index": obs.frame_index,
                "timestamp_s": obs.timestamp_s,
                "class_id": obs.class_id,
                "class_name": obs.class_name,
                "global_track_id": obs.global_track_id,
                "local_track_id": obs.local_track_id,
                "bbox_xyxy": list(obs.bbox_xyxy),
                "center_xy": list(obs.center),
                "confidence": obs.confidence,
                "status": row["status"],
                "eligible": row["eligible"],
                "is_background": row["is_background"],
                "background_iou": row["background_iou"],
                "background_source_track_id": row["background_source_track_id"],
                "age_s": row["age_s"],
                "hits": row["hits"],
                "high_conf_hits": row["high_conf_hits"],
                "max_confidence": row["max_confidence"],
                "mean_confidence": row["mean_confidence"],
            }
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def draw_runtime_tracks(
    frame_bgr,
    enriched_rows,
    trails,
    candidate_only=False,
    max_trail_points=30,
):
    import cv2

    out = frame_bgr.copy()
    for row in enriched_rows:
        if candidate_only and not row["eligible"]:
            continue

        obs = row["observation"]
        x1, y1, x2, y2 = map(int, obs.bbox_xyxy)

        if row["status"] == "BACKGROUND":
            color = (110, 110, 110)
        elif row["status"] == "ELIGIBLE":
            color = (0, 220, 0) if obs.class_id == 0 else (0, 210, 255)
        else:
            color = (180, 180, 180)

        label = (
            f"{obs.class_name} ID={obs.global_track_id} "
            f"{obs.confidence:.2f} {row['status']}"
        )
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2 if row["eligible"] else 1)
        cv2.putText(
            out,
            label,
            (x1, max(18, y1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            color,
            1,
            cv2.LINE_AA,
        )

        if row["status"] != "BACKGROUND":
            cx, cy = map(int, obs.center)
            trail = trails.setdefault(obs.global_track_id, [])
            trail.append((cx, cy))
            if len(trail) > max_trail_points:
                del trail[:-max_trail_points]
            if len(trail) >= 2 and not candidate_only:
                pts = np.asarray(trail, dtype=np.int32).reshape(-1, 1, 2)
                cv2.polylines(out, [pts], False, color, 1)

    return out
