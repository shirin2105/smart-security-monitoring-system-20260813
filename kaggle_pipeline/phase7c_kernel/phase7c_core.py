from __future__ import annotations

from dataclasses import dataclass, asdict, field
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
import json
import math
import numpy as np

try:
    from .placement_transition import placement_transition_features
except ImportError:  # direct kernel import used by notebook/unit entrypoints
    from placement_transition import placement_transition_features


# ---------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------

@dataclass
class QualityConfig:
    window_s: float = 2.0
    min_samples: int = 5

    person_min_duration_s: float = 0.7
    person_high_conf: float = 0.40
    person_median_conf: float = 0.40
    person_rolling_high_ratio: float = 0.30
    person_min_rolling_good_ratio: float = 0.50
    person_min_global_high_ratio: float = 0.30

    luggage_min_duration_s: float = 1.5
    luggage_high_conf: float = 0.35
    luggage_median_conf: float = 0.35
    luggage_rolling_high_ratio: float = 0.50
    luggage_min_rolling_good_ratio: float = 0.50
    luggage_min_global_high_ratio: float = 0.50


@dataclass
class StitchConfig:
    max_gap_s: float = 0.80
    max_center_distance_px: float = 80.0
    max_normalized_distance: float = 1.20


@dataclass
class StationaryConfig:
    window_s: float = 2.0
    min_samples: int = 10
    max_spread_norm: float = 0.15
    max_net_displacement_norm: float = 0.20
    hold_s: float = 3.0


@dataclass
class OwnerConfig:
    near_norm: float = 0.50
    min_overlap_s: float = 0.70
    min_association_score: float = 0.45
    away_hold_s: float = 5.0
    placement_window_s: float = 3.0


@dataclass
class Phase7CConfig:
    quality: QualityConfig = field(default_factory=QualityConfig)
    stitch: StitchConfig = field(default_factory=StitchConfig)
    stationary: StationaryConfig = field(default_factory=StationaryConfig)
    owner: OwnerConfig = field(default_factory=OwnerConfig)
    roi_polygon: Optional[List[Tuple[float, float]]] = None
    diagnostics_enabled: bool = False


@dataclass
class TrackQualityProfile:
    track_id: int
    class_name: str
    start_s: float
    end_s: float
    duration_s: float
    observations: int
    mean_confidence: float
    median_confidence: float
    high_conf_ratio: float
    rolling_good_ratio: float
    passed: bool


@dataclass
class PhysicalLuggage:
    physical_id: str
    source_track_ids: List[int]
    rows: List[dict]
    stitch_links: List[dict]


@dataclass
class StationaryRun:
    start_s: float
    end_s: float
    confirmed_at_s: float
    duration_s: float
    start_index: int
    end_index: int


@dataclass
class OwnerAssociation:
    physical_id: str
    person_track_id: Optional[int]
    association_score: float
    inside_ratio: float
    near_ratio: float
    overlap_frames: int
    overlap_s: float
    owner_last_near_s: Optional[float]
    owner_last_visible_s: Optional[float] = None
    candidates: List[dict] = field(default_factory=list)
    rejection_reason: Optional[str] = None
    selection_reason: Optional[str] = None
    history_window_start_s: Optional[float] = None
    history_window_end_s: Optional[float] = None


@dataclass
class AbandonedCandidate:
    event_id: str
    physical_id: str
    source_track_ids: List[int]
    owner_person_track_id: int
    stationary_start_s: float
    stationary_confirmed_s: float
    owner_last_near_s: float
    candidate_time_s: float
    owner_away_s: float
    association_score: float
    bbox_xyxy: List[float]
    center_xy: List[float]
    status: str = "ABANDONED_OBJECT_CANDIDATE"


# ---------------------------------------------------------------------
# Basic helpers
# ---------------------------------------------------------------------

def load_jsonl(path: str | Path) -> List[dict]:
    rows = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    rows.sort(key=lambda r: (int(r["frame_index"]), int(r["global_track_id"])))
    return rows


def group_tracks(rows: Sequence[dict]) -> Dict[int, List[dict]]:
    out = defaultdict(list)
    for r in rows:
        out[int(r["global_track_id"])].append(r)
    for rs in out.values():
        rs.sort(key=lambda r: float(r["timestamp_s"]))
    return dict(out)


def bbox_diag(box: Sequence[float]) -> float:
    x1, y1, x2, y2 = map(float, box)
    return max(1.0, math.hypot(max(1.0, x2 - x1), max(1.0, y2 - y1)))


def center_distance(a: Sequence[float], b: Sequence[float]) -> float:
    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def point_to_bbox_distance(point: Sequence[float], box: Sequence[float]) -> float:
    x, y = map(float, point)
    x1, y1, x2, y2 = map(float, box)
    dx = max(x1 - x, 0.0, x - x2)
    dy = max(y1 - y, 0.0, y - y2)
    return math.hypot(dx, dy)


def point_in_polygon(point: Sequence[float], polygon: Optional[Sequence[Sequence[float]]]) -> bool:
    if not polygon:
        return True
    x, y = map(float, point)
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = map(float, polygon[i])
        xj, yj = map(float, polygon[j])
        crosses = ((yi > y) != (yj > y))
        if crosses:
            x_intersect = (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi
            if x < x_intersect:
                inside = not inside
        j = i
    return inside


# ---------------------------------------------------------------------
# Rolling quality gate
# ---------------------------------------------------------------------

def _quality_params(class_name: str, cfg: QualityConfig):
    if class_name == "person":
        return {
            "min_duration": cfg.person_min_duration_s,
            "high_conf": cfg.person_high_conf,
            "median_conf": cfg.person_median_conf,
            "rolling_ratio": cfg.person_rolling_high_ratio,
            "min_rolling_good_ratio": cfg.person_min_rolling_good_ratio,
            "min_global_high_ratio": cfg.person_min_global_high_ratio,
        }
    if class_name == "luggage":
        return {
            "min_duration": cfg.luggage_min_duration_s,
            "high_conf": cfg.luggage_high_conf,
            "median_conf": cfg.luggage_median_conf,
            "rolling_ratio": cfg.luggage_rolling_high_ratio,
            "min_rolling_good_ratio": cfg.luggage_min_rolling_good_ratio,
            "min_global_high_ratio": cfg.luggage_min_global_high_ratio,
        }
    raise ValueError(f"Unsupported class_name={class_name}")


def quality_profile(track_rows: Sequence[dict], cfg: QualityConfig) -> TrackQualityProfile:
    if not track_rows:
        raise ValueError("track_rows is empty")

    rows = sorted(track_rows, key=lambda r: float(r["timestamp_s"]))
    cls = str(rows[0]["class_name"])
    p = _quality_params(cls, cfg)

    ts = np.asarray([float(r["timestamp_s"]) for r in rows], dtype=np.float64)
    conf = np.asarray([float(r["confidence"]) for r in rows], dtype=np.float64)

    rolling_good = []
    left = 0
    for i, t in enumerate(ts):
        while left < i and ts[left] < t - cfg.window_s:
            left += 1
        c = conf[left:i + 1]
        good = (
            len(c) >= cfg.min_samples
            and float(np.median(c)) >= p["median_conf"]
            and float(np.mean(c >= p["high_conf"])) >= p["rolling_ratio"]
        )
        rolling_good.append(bool(good))

    start_s = float(ts[0])
    end_s = float(ts[-1])
    duration_s = max(0.0, end_s - start_s)
    global_high_ratio = float(np.mean(conf >= p["high_conf"]))
    rolling_good_ratio = float(np.mean(rolling_good))

    passed = bool(
        duration_s >= p["min_duration"]
        and float(np.median(conf)) >= p["median_conf"]
        and global_high_ratio >= p["min_global_high_ratio"]
        and rolling_good_ratio >= p["min_rolling_good_ratio"]
    )

    return TrackQualityProfile(
        track_id=int(rows[0]["global_track_id"]),
        class_name=cls,
        start_s=start_s,
        end_s=end_s,
        duration_s=duration_s,
        observations=len(rows),
        mean_confidence=float(np.mean(conf)),
        median_confidence=float(np.median(conf)),
        high_conf_ratio=global_high_ratio,
        rolling_good_ratio=rolling_good_ratio,
        passed=passed,
    )


def build_quality_report(rows: Sequence[dict], cfg: QualityConfig):
    tracks = group_tracks(rows)
    profiles = {}
    for track_id, rs in tracks.items():
        profiles[track_id] = quality_profile(rs, cfg)
    return profiles


# ---------------------------------------------------------------------
# Physical-object stitching for luggage
# ---------------------------------------------------------------------

def _stitch_cost(a_rows: Sequence[dict], b_rows: Sequence[dict], cfg: StitchConfig):
    a_end = a_rows[-1]
    b_start = b_rows[0]
    gap = float(b_start["timestamp_s"]) - float(a_end["timestamp_s"])
    if gap < 0.0 or gap > cfg.max_gap_s:
        return None

    dist_px = center_distance(a_end["center_xy"], b_start["center_xy"])
    norm = dist_px / max(
        bbox_diag(a_end["bbox_xyxy"]),
        bbox_diag(b_start["bbox_xyxy"]),
    )

    if dist_px > cfg.max_center_distance_px or norm > cfg.max_normalized_distance:
        return None

    # Lower is better. Gap and spatial distance both matter.
    cost = (gap / max(cfg.max_gap_s, 1e-9)) + norm
    return {
        "gap_s": gap,
        "center_distance_px": dist_px,
        "normalized_distance": norm,
        "cost": cost,
    }


def stitch_luggage_tracks(
    rows: Sequence[dict],
    quality_profiles: Dict[int, TrackQualityProfile],
    cfg: StitchConfig,
) -> List[PhysicalLuggage]:
    tracks = group_tracks(rows)

    eligible = []
    for track_id, rs in tracks.items():
        prof = quality_profiles[track_id]
        if prof.class_name == "luggage" and prof.passed:
            eligible.append((track_id, rs))
    eligible.sort(key=lambda x: float(x[1][0]["timestamp_s"]))

    # Greedy chain construction. Only quality-passed luggage is stitchable.
    used = set()
    physical = []
    counter = 1

    for i, (track_id, rs) in enumerate(eligible):
        if track_id in used:
            continue

        chain_ids = [track_id]
        chain_rows = list(rs)
        links = []
        used.add(track_id)
        current_rows = rs

        while True:
            best = None
            for next_id, next_rows in eligible:
                if next_id in used:
                    continue
                info = _stitch_cost(current_rows, next_rows, cfg)
                if info is None:
                    continue
                if best is None or info["cost"] < best[0]:
                    best = (info["cost"], next_id, next_rows, info)

            if best is None:
                break

            _, next_id, next_rows, info = best
            links.append({
                "from_track_id": int(chain_ids[-1]),
                "to_track_id": int(next_id),
                **{k: float(v) for k, v in info.items()},
            })
            chain_ids.append(int(next_id))
            chain_rows.extend(next_rows)
            chain_rows.sort(key=lambda r: float(r["timestamp_s"]))
            current_rows = next_rows
            used.add(next_id)

        physical.append(
            PhysicalLuggage(
                physical_id=f"LUG_{counter:04d}",
                source_track_ids=[int(x) for x in chain_ids],
                rows=chain_rows,
                stitch_links=links,
            )
        )
        counter += 1

    return physical


# ---------------------------------------------------------------------
# Stationary detection
# ---------------------------------------------------------------------

def stationary_samples(rows: Sequence[dict], cfg: StationaryConfig):
    rows = sorted(rows, key=lambda r: float(r["timestamp_s"]))
    ts = np.asarray([float(r["timestamp_s"]) for r in rows], dtype=np.float64)
    centers = np.asarray([r["center_xy"] for r in rows], dtype=np.float64)
    boxes = np.asarray([r["bbox_xyxy"] for r in rows], dtype=np.float64)

    result = []
    left = 0

    for i, t in enumerate(ts):
        while left < i and ts[left] < t - cfg.window_s:
            left += 1

        c = centers[left:i + 1]
        b = boxes[left:i + 1]

        if len(c) < cfg.min_samples:
            result.append({
                "timestamp_s": float(t),
                "is_stationary": False,
                "spread_norm": None,
                "net_norm": None,
            })
            continue

        med = np.median(c, axis=0)
        spread_px = float(np.percentile(np.linalg.norm(c - med, axis=1), 90))
        widths = np.maximum(1.0, b[:, 2] - b[:, 0])
        heights = np.maximum(1.0, b[:, 3] - b[:, 1])
        diag = float(np.median(np.sqrt(widths * widths + heights * heights)))

        spread_norm = spread_px / max(diag, 1.0)
        net_norm = float(np.linalg.norm(c[-1] - c[0])) / max(diag, 1.0)

        is_stationary = (
            spread_norm <= cfg.max_spread_norm
            and net_norm <= cfg.max_net_displacement_norm
        )

        result.append({
            "timestamp_s": float(t),
            "is_stationary": bool(is_stationary),
            "spread_norm": float(spread_norm),
            "net_norm": float(net_norm),
        })

    return result


def find_stationary_runs(rows: Sequence[dict], cfg: StationaryConfig) -> List[StationaryRun]:
    samples = stationary_samples(rows, cfg)
    runs = []
    start_idx = None

    for i, s in enumerate(samples):
        if s["is_stationary"] and start_idx is None:
            start_idx = i

        ended = (not s["is_stationary"]) or (i == len(samples) - 1)

        if start_idx is not None and ended:
            end_idx = i - 1 if not s["is_stationary"] else i
            start_s = float(samples[start_idx]["timestamp_s"])
            end_s = float(samples[end_idx]["timestamp_s"])
            duration = max(0.0, end_s - start_s)

            if duration >= cfg.hold_s:
                runs.append(
                    StationaryRun(
                        start_s=start_s,
                        end_s=end_s,
                        confirmed_at_s=start_s + cfg.hold_s,
                        duration_s=duration,
                        start_index=start_idx,
                        end_index=end_idx,
                    )
                )
            start_idx = None

    return runs


# ---------------------------------------------------------------------
# Owner association
# ---------------------------------------------------------------------

def associate_owner(
    physical: PhysicalLuggage,
    stationary_run: StationaryRun,
    person_tracks: Dict[int, List[dict]],
    quality_profiles: Dict[int, TrackQualityProfile],
    cfg: OwnerConfig,
    fps_hint: float = 30.0,
    diagnostics_enabled: bool = False,
) -> OwnerAssociation:
    physical_luggage_first_seen_s = float(physical.rows[0]["timestamp_s"])
    history_end_s = float(stationary_run.start_s)
    history_start_s = max(
        physical_luggage_first_seen_s,
        history_end_s - float(cfg.placement_window_s),
    )

    # Use bag history within placement window [history_start_s, history_end_s]
    bag_rows = [
        r for r in physical.rows
        if history_start_s <= float(r["timestamp_s"]) <= history_end_s
    ]
    bag_by_frame = {int(r["frame_index"]): r for r in bag_rows}

    best = None
    candidates = []

    for person_id, prs in person_tracks.items():
        prof = quality_profiles.get(person_id)
        if prof is None or prof.class_name != "person":
            continue

        person_by_frame = {int(r["frame_index"]): r for r in prs}
        distances = []
        distances_px = []
        candidate_bboxes = []
        overlap_times = []
        synchronized_observations = []

        for frame_idx, bag_r in bag_by_frame.items():
            person_r = person_by_frame.get(frame_idx)
            if person_r is None:
                continue
            d = point_to_bbox_distance(
                bag_r["center_xy"],
                person_r["bbox_xyxy"],
            )
            d_norm = d / bbox_diag(person_r["bbox_xyxy"])
            distances_px.append(float(d))
            distances.append(float(d_norm))
            candidate_bboxes.append([float(v) for v in person_r["bbox_xyxy"]])
            overlap_times.append(float(person_r["timestamp_s"]))
            synchronized_observations.append({
                "timestamp_s": float(person_r["timestamp_s"]),
                "bag_center": [float(v) for v in bag_r["center_xy"]],
                "person_center": [float(v) for v in person_r["center_xy"]],
                "person_bbox": [float(v) for v in person_r["bbox_xyxy"]],
            })

        overlap_frames = len(distances)
        overlap_s = overlap_frames / max(fps_hint, 1e-9)
        arr = np.asarray(distances, dtype=np.float64)
        inside_ratio = float(np.mean(arr <= 1e-9)) if len(arr) else 0.0
        near_ratio = float(np.mean(arr <= cfg.near_norm)) if len(arr) else 0.0
        overlap_term = min(overlap_s / max(cfg.placement_window_s, 1e-9), 1.0)
        min_distance_norm = float(np.min(arr)) if len(arr) else None
        proximity_ratio = (
            max(0.0, 1.0 - min_distance_norm / max(cfg.near_norm, 1e-9))
            if min_distance_norm is not None else 0.0
        )
        # Closest approach is retained as diagnostic evidence. Production
        # selection keeps the frozen containment/near/overlap weighting.
        proximity_component = 0.65 * proximity_ratio
        inside_component = 0.65 * inside_ratio
        near_component = 0.25 * near_ratio
        overlap_component = 0.10 * overlap_term
        score = inside_component + near_component + overlap_component
        eligible = bool(prof.passed and overlap_s >= cfg.min_overlap_s)

        item = {
            "person_track_id": int(person_id),
            "association_score": float(score),
            "inside_ratio": inside_ratio,
            "near_ratio": near_ratio,
            "overlap_frames": int(overlap_frames),
            "overlap_s": float(overlap_s),
            "quality_pass": bool(prof.passed),
            "first_seen_s": min(overlap_times) if overlap_times else None,
            "last_seen_s": max(overlap_times) if overlap_times else None,
            "track_age_s": max(overlap_times) - min(overlap_times) if overlap_times else 0.0,
            "min_distance_norm": min_distance_norm,
            # Keep diagnostic evidence bounded for long tracks.
            "candidate_bboxes": candidate_bboxes[-5:],
        }
        if diagnostics_enabled:
            placement = placement_transition_features(synchronized_observations)
            frame_indices = sorted(person_by_frame)
            strides = np.diff(frame_indices)
            typical_stride = float(np.median(strides)) if len(strides) else 0.0
            item.update({
                "inside_score_component": float(inside_component),
                "proximity_ratio": float(proximity_ratio),
                "proximity_score_component": float(proximity_component),
                "near_score_component": float(near_component),
                "overlap_score_component": float(overlap_component),
                "overlap_term": float(overlap_term),
                "temporal_overlap_ratio": overlap_frames / max(len(bag_by_frame), 1),
                "candidate_eligible": eligible,
                "candidate_selected": False,
                "min_association_score": float(cfg.min_association_score),
                "person_confidence": max((float(row["confidence"]) for row in prs), default=0.0),
                "min_distance_px": float(np.min(distances_px)) if distances_px else None,
                "candidate_present_before_stationary": bool(overlap_times and min(overlap_times) < stationary_run.start_s),
                "candidate_present_at_stationary": int(round(stationary_run.start_s * fps_hint)) in person_by_frame,
                "candidate_present_after_stationary": any(float(row["timestamp_s"]) > stationary_run.start_s for row in prs),
                "person_track_fragmented": bool(
                    len(strides) and typical_stride > 0 and np.max(strides) > 1.5 * typical_stride
                ),
                "placement_transition": placement,
            })
        candidates.append(item)

        if not prof.passed or overlap_s < cfg.min_overlap_s:
            continue
        if best is None or item["association_score"] > best["association_score"]:
            best = item

    if best is None or best["association_score"] < cfg.min_association_score:
        if not candidates:
            reason = "NO_PERSON_CANDIDATES"
        elif not any(item["quality_pass"] for item in candidates):
            reason = "CANDIDATE_TRACK_TOO_SHORT"
        elif not any(item["overlap_frames"] for item in candidates):
            reason = "OWNER_HISTORY_NOT_AVAILABLE"
        elif not any(item["overlap_s"] >= cfg.min_overlap_s for item in candidates):
            reason = "CANDIDATE_TRACK_TOO_SHORT"
        elif not any(item["near_ratio"] > 0 or item["inside_ratio"] > 0 for item in candidates):
            reason = "NO_PERSON_WITHIN_DISTANCE"
        else:
            reason = "CANDIDATE_SCORE_BELOW_THRESHOLD"
        return OwnerAssociation(
            physical_id=physical.physical_id,
            person_track_id=None,
            association_score=float(best["association_score"]) if best else 0.0,
            inside_ratio=float(best["inside_ratio"]) if best else 0.0,
            near_ratio=float(best["near_ratio"]) if best else 0.0,
            overlap_frames=int(best["overlap_frames"]) if best else 0,
            overlap_s=float(best["overlap_s"]) if best else 0.0,
            owner_last_near_s=None,
            owner_last_visible_s=None,
            candidates=candidates,
            rejection_reason=reason,
            history_window_start_s=history_start_s,
            history_window_end_s=history_end_s,
        )

    owner_id = int(best["person_track_id"])
    if diagnostics_enabled:
        best["candidate_selected"] = True
    owner_rows = person_tracks[owner_id]
    owner_by_frame = {int(r["frame_index"]): r for r in owner_rows}

    # Product Policy v2: the abandonment trigger requires the owner to be absent
    # from the camera view, not merely standing far from the bag. Track the last
    # frame in which the owner track is observed anywhere in the scene.
    owner_last_visible_s = float(owner_rows[-1]["timestamp_s"]) if owner_rows else None

    last_near = None
    for bag_r in physical.rows:
        person_r = owner_by_frame.get(int(bag_r["frame_index"]))
        if person_r is None:
            continue
        d = point_to_bbox_distance(
            bag_r["center_xy"],
            person_r["bbox_xyxy"],
        )
        d_norm = d / bbox_diag(person_r["bbox_xyxy"])
        if d_norm <= cfg.near_norm:
            last_near = float(bag_r["timestamp_s"])

    return OwnerAssociation(
        physical_id=physical.physical_id,
        person_track_id=owner_id,
        association_score=float(best["association_score"]),
        inside_ratio=float(best["inside_ratio"]),
        near_ratio=float(best["near_ratio"]),
        overlap_frames=int(best["overlap_frames"]),
        overlap_s=float(best["overlap_s"]),
        owner_last_near_s=last_near,
        owner_last_visible_s=owner_last_visible_s,
        candidates=candidates,
        selection_reason="highest_association_score",
        history_window_start_s=history_start_s,
        history_window_end_s=history_end_s,
    )


# ---------------------------------------------------------------------
# Event engine
# ---------------------------------------------------------------------

def nearest_row_at_or_after(rows: Sequence[dict], timestamp_s: float) -> Optional[dict]:
    for r in rows:
        if float(r["timestamp_s"]) >= timestamp_s:
            return r
    return None


def infer_phase7c(
    rows: Sequence[dict],
    cfg: Phase7CConfig,
    fps_hint: float = 30.0,
):
    tracks = group_tracks(rows)
    quality = build_quality_report(rows, cfg.quality)

    person_tracks = {
        tid: rs for tid, rs in tracks.items()
        if rs and rs[0]["class_name"] == "person"
    }

    physical_luggage = stitch_luggage_tracks(rows, quality, cfg.stitch)

    events: List[AbandonedCandidate] = []
    physical_reports = []
    owner_reports = []
    owner_prechecks = []
    timeline_rows = []

    event_counter = 1

    for physical in physical_luggage:
        stationary_runs = find_stationary_runs(physical.rows, cfg.stationary)

        physical_report = {
            "physical_id": physical.physical_id,
            "source_track_ids": physical.source_track_ids,
            "start_s": float(physical.rows[0]["timestamp_s"]),
            "end_s": float(physical.rows[-1]["timestamp_s"]),
            "duration_s": float(
                float(physical.rows[-1]["timestamp_s"])
                - float(physical.rows[0]["timestamp_s"])
            ),
            "stitch_links": physical.stitch_links,
            "stationary_runs": [asdict(r) for r in stationary_runs],
        }
        physical_reports.append(physical_report)

        # Build sample-wise stationary flag for timeline.
        stat_samples = stationary_samples(physical.rows, cfg.stationary)

        chosen_owner = None
        chosen_run = None
        chosen_event = None

        for run in stationary_runs:
            # Product Policy v2: ABANDONED_OBJECT is evaluated over the full camera
            # frame. No valid-floor ROI is used to include or exclude luggage.
            row_for_roi = nearest_row_at_or_after(physical.rows, run.confirmed_at_s)
            if row_for_roi is None:
                owner_prechecks.append({
                    "physical_id": physical.physical_id,
                    "stationary_start_s": float(run.start_s),
                    "stationary_confirmed_s": float(run.confirmed_at_s),
                    "eligible": False,
                    "rejection_reason": "NO_LUGGAGE_ROW_AT_STATIONARY_CONFIRM",
                })
                continue
            owner_prechecks.append({
                "physical_id": physical.physical_id,
                "stationary_start_s": float(run.start_s),
                "stationary_confirmed_s": float(run.confirmed_at_s),
                "eligible": True,
                "rejection_reason": None,
            })

            owner = associate_owner(
                physical,
                run,
                person_tracks,
                quality,
                cfg.owner,
                fps_hint=fps_hint,
                diagnostics_enabled=cfg.diagnostics_enabled,
            )
            owner_reports.append(asdict(owner))

            if (
                owner.person_track_id is None
                or owner.owner_last_near_s is None
                or owner.owner_last_visible_s is None
            ):
                continue

            # Product Policy v2: the abandonment trigger is the owner being absent
            # from the camera view (not merely far from the bag) for away_hold_s.
            candidate_time = max(
                run.confirmed_at_s,
                float(owner.owner_last_visible_s) + cfg.owner.away_hold_s,
            )

            # The luggage must remain in the SAME stationary run until candidate time.
            if candidate_time > run.end_s:
                continue

            event_row = nearest_row_at_or_after(physical.rows, candidate_time)
            if event_row is None:
                continue
            if float(event_row["timestamp_s"]) > run.end_s + 1e-6:
                continue

            chosen_owner = owner
            chosen_run = run
            chosen_event = AbandonedCandidate(
                event_id=f"AO_{event_counter:04d}",
                physical_id=physical.physical_id,
                source_track_ids=physical.source_track_ids,
                owner_person_track_id=int(owner.person_track_id),
                stationary_start_s=float(run.start_s),
                stationary_confirmed_s=float(run.confirmed_at_s),
                owner_last_near_s=float(owner.owner_last_near_s),
                candidate_time_s=float(event_row["timestamp_s"]),
                owner_away_s=float(
                    float(event_row["timestamp_s"]) - float(owner.owner_last_near_s)
                ),
                association_score=float(owner.association_score),
                bbox_xyxy=[float(v) for v in event_row["bbox_xyxy"]],
                center_xy=[float(v) for v in event_row["center_xy"]],
            )
            events.append(chosen_event)
            event_counter += 1
            break

        # Timeline state
        current_stat_start = None
        for row, sample in zip(physical.rows, stat_samples):
            t = float(row["timestamp_s"])
            if sample["is_stationary"]:
                if current_stat_start is None:
                    current_stat_start = t
            else:
                current_stat_start = None

            state = "MOVING"
            if sample["is_stationary"]:
                state = "STATIONARY_PENDING"
                if (
                    current_stat_start is not None
                    and t - current_stat_start >= cfg.stationary.hold_s
                ):
                    state = "STATIONARY"

            if chosen_owner and chosen_owner.owner_last_visible_s is not None:
                if t >= float(chosen_owner.owner_last_visible_s) + cfg.owner.away_hold_s:
                    if state == "STATIONARY":
                        state = "OWNER_AWAY"

            if chosen_event and t >= chosen_event.candidate_time_s:
                state = "ABANDONED_OBJECT_CANDIDATE"

            timeline_rows.append({
                "frame_index": int(row["frame_index"]),
                "timestamp_s": t,
                "physical_id": physical.physical_id,
                "source_track_id": int(row["global_track_id"]),
                "bbox_xyxy": [float(v) for v in row["bbox_xyxy"]],
                "center_xy": [float(v) for v in row["center_xy"]],
                "confidence": float(row["confidence"]),
                "state": state,
                "owner_person_track_id": (
                    int(chosen_owner.person_track_id)
                    if chosen_owner and chosen_owner.person_track_id is not None
                    else None
                ),
                "stationary_spread_norm": sample["spread_norm"],
                "stationary_net_norm": sample["net_norm"],
            })

    quality_report = {
        str(tid): asdict(profile)
        for tid, profile in sorted(quality.items())
    }

    summary = {
        "input_rows": len(rows),
        "input_tracks": len(tracks),
        "quality_pass_person_tracks": sum(
            1 for p in quality.values()
            if p.class_name == "person" and p.passed
        ),
        "quality_pass_luggage_tracks": sum(
            1 for p in quality.values()
            if p.class_name == "luggage" and p.passed
        ),
        "physical_luggage_objects": len(physical_luggage),
        "stitch_links": sum(len(p.stitch_links) for p in physical_luggage),
        "owner_associations_attempted": len(owner_reports),
        "abandoned_candidates": len(events),
    }

    return {
        "summary": summary,
        "quality_report": quality_report,
        "physical_luggage": physical_reports,
        "owner_prechecks": owner_prechecks,
        "owner_associations": owner_reports,
        "events": [asdict(e) for e in events],
        "timeline": timeline_rows,
    }


# ---------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------

def annotate_video(
    video_path: str | Path,
    source_rows: Sequence[dict],
    result: dict,
    output_path: str | Path,
):
    import cv2

    video_path = str(video_path)
    output_path = str(output_path)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = float(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    writer = cv2.VideoWriter(
        output_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps if fps > 0 else 30.0,
        (width, height),
    )
    if not writer.isOpened():
        raise RuntimeError(f"Could not create output: {output_path}")

    timeline_by_frame = defaultdict(list)
    for row in result["timeline"]:
        timeline_by_frame[int(row["frame_index"])].append(row)

    # Only quality-passed persons are useful for owner display.
    quality = result["quality_report"]
    person_by_frame = defaultdict(list)
    for r in source_rows:
        if r["class_name"] != "person":
            continue
        q = quality.get(str(int(r["global_track_id"])))
        if q and q["passed"]:
            person_by_frame[int(r["frame_index"])].append(r)

    event_by_physical = {
        e["physical_id"]: e for e in result["events"]
    }

    frame_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        # Persons: subdued owner/context boxes.
        for p in person_by_frame.get(frame_idx, []):
            x1, y1, x2, y2 = map(int, p["bbox_xyxy"])
            cv2.rectangle(frame, (x1, y1), (x2, y2), (120, 200, 120), 1)
            cv2.putText(
                frame,
                f"P {int(p['global_track_id'])}",
                (x1, max(16, y1 - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (120, 200, 120),
                1,
                cv2.LINE_AA,
            )

        for item in timeline_by_frame.get(frame_idx, []):
            x1, y1, x2, y2 = map(int, item["bbox_xyxy"])
            state = item["state"]

            if state == "MOVING":
                color = (180, 180, 180)
            elif state == "STATIONARY_PENDING":
                color = (0, 200, 255)
            elif state == "STATIONARY":
                color = (0, 165, 255)
            elif state == "OWNER_AWAY":
                color = (0, 100, 255)
            else:
                color = (0, 0, 255)

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label = f"{item['physical_id']} {state}"
            if item["owner_person_track_id"] is not None:
                label += f" owner={item['owner_person_track_id']}"
            cv2.putText(
                frame,
                label,
                (x1, max(18, y1 - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                color,
                1,
                cv2.LINE_AA,
            )

        # Persistent banner once an event has fired.
        active_events = [
            e for e in result["events"]
            if frame_idx / max(fps, 1e-9) >= e["candidate_time_s"]
        ]
        if active_events:
            e = active_events[-1]
            cv2.rectangle(frame, (0, 0), (width, 38), (0, 0, 180), -1)
            cv2.putText(
                frame,
                (
                    f"ABANDONED OBJECT CANDIDATE {e['event_id']} "
                    f"owner={e['owner_person_track_id']}"
                ),
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

        writer.write(frame)
        frame_idx += 1

    cap.release()
    writer.release()
