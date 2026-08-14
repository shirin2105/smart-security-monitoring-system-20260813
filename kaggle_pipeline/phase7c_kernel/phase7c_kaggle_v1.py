"""
PHASE 7C v1 — offline abandoned-object reasoning over Phase7B.1 tracks.

No detector inference.
No GPU required.
No retraining.

Inputs:
  TRACKS_V4_PATH=/kaggle/input/.../tracks_v4.jsonl
  VIDEO_PATH=/kaggle/input/.../aboda-video1.avi  # optional but recommended

Outputs:
  /kaggle/working/phase7c_v1/
    phase7c_summary.json
    quality_report.json
    physical_luggage.json
    owner_associations.json
    phase7c_events.json
    phase7c_timeline.jsonl
    annotated_phase7c.mp4   # if VIDEO_PATH supplied
"""

from __future__ import annotations
import os
import sys
import json
import subprocess
from pathlib import Path

WORK = Path("/kaggle/working")
INPUT = Path("/kaggle/input")
OUT = WORK / "phase7c_v1"

EMBEDDED_CORE = 'from __future__ import annotations\n\nfrom dataclasses import dataclass, asdict, field\nfrom collections import defaultdict\nfrom pathlib import Path\nfrom typing import Dict, List, Optional, Sequence, Tuple\nimport json\nimport math\nimport numpy as np\n\n\n# ---------------------------------------------------------------------\n# Data types\n# ---------------------------------------------------------------------\n\n@dataclass\nclass QualityConfig:\n    window_s: float = 2.0\n    min_samples: int = 5\n\n    person_min_duration_s: float = 0.7\n    person_high_conf: float = 0.40\n    person_median_conf: float = 0.40\n    person_rolling_high_ratio: float = 0.30\n    person_min_rolling_good_ratio: float = 0.50\n    person_min_global_high_ratio: float = 0.30\n\n    luggage_min_duration_s: float = 1.5\n    luggage_high_conf: float = 0.35\n    luggage_median_conf: float = 0.35\n    luggage_rolling_high_ratio: float = 0.50\n    luggage_min_rolling_good_ratio: float = 0.50\n    luggage_min_global_high_ratio: float = 0.50\n\n\n@dataclass\nclass StitchConfig:\n    max_gap_s: float = 0.80\n    max_center_distance_px: float = 80.0\n    max_normalized_distance: float = 1.20\n\n\n@dataclass\nclass StationaryConfig:\n    window_s: float = 2.0\n    min_samples: int = 10\n    max_spread_norm: float = 0.15\n    max_net_displacement_norm: float = 0.20\n    hold_s: float = 3.0\n\n\n@dataclass\nclass OwnerConfig:\n    near_norm: float = 0.50\n    min_overlap_s: float = 0.70\n    min_association_score: float = 0.60\n    away_hold_s: float = 5.0\n\n\n@dataclass\nclass Phase7CConfig:\n    quality: QualityConfig = field(default_factory=QualityConfig)\n    stitch: StitchConfig = field(default_factory=StitchConfig)\n    stationary: StationaryConfig = field(default_factory=StationaryConfig)\n    owner: OwnerConfig = field(default_factory=OwnerConfig)\n    roi_polygon: Optional[List[Tuple[float, float]]] = None\n\n\n@dataclass\nclass TrackQualityProfile:\n    track_id: int\n    class_name: str\n    start_s: float\n    end_s: float\n    duration_s: float\n    observations: int\n    mean_confidence: float\n    median_confidence: float\n    high_conf_ratio: float\n    rolling_good_ratio: float\n    passed: bool\n\n\n@dataclass\nclass PhysicalLuggage:\n    physical_id: str\n    source_track_ids: List[int]\n    rows: List[dict]\n    stitch_links: List[dict]\n\n\n@dataclass\nclass StationaryRun:\n    start_s: float\n    end_s: float\n    confirmed_at_s: float\n    duration_s: float\n    start_index: int\n    end_index: int\n\n\n@dataclass\nclass OwnerAssociation:\n    physical_id: str\n    person_track_id: Optional[int]\n    association_score: float\n    inside_ratio: float\n    near_ratio: float\n    overlap_frames: int\n    overlap_s: float\n    owner_last_near_s: Optional[float]\n\n\n@dataclass\nclass AbandonedCandidate:\n    event_id: str\n    physical_id: str\n    source_track_ids: List[int]\n    owner_person_track_id: int\n    stationary_start_s: float\n    stationary_confirmed_s: float\n    owner_last_near_s: float\n    candidate_time_s: float\n    owner_away_s: float\n    association_score: float\n    bbox_xyxy: List[float]\n    center_xy: List[float]\n    status: str = "ABANDONED_OBJECT_CANDIDATE"\n\n\n# ---------------------------------------------------------------------\n# Basic helpers\n# ---------------------------------------------------------------------\n\ndef load_jsonl(path: str | Path) -> List[dict]:\n    rows = []\n    with Path(path).open("r", encoding="utf-8") as f:\n        for line in f:\n            line = line.strip()\n            if line:\n                rows.append(json.loads(line))\n    rows.sort(key=lambda r: (int(r["frame_index"]), int(r["global_track_id"])))\n    return rows\n\n\ndef group_tracks(rows: Sequence[dict]) -> Dict[int, List[dict]]:\n    out = defaultdict(list)\n    for r in rows:\n        out[int(r["global_track_id"])].append(r)\n    for rs in out.values():\n        rs.sort(key=lambda r: float(r["timestamp_s"]))\n    return dict(out)\n\n\ndef bbox_diag(box: Sequence[float]) -> float:\n    x1, y1, x2, y2 = map(float, box)\n    return max(1.0, math.hypot(max(1.0, x2 - x1), max(1.0, y2 - y1)))\n\n\ndef center_distance(a: Sequence[float], b: Sequence[float]) -> float:\n    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))\n\n\ndef point_to_bbox_distance(point: Sequence[float], box: Sequence[float]) -> float:\n    x, y = map(float, point)\n    x1, y1, x2, y2 = map(float, box)\n    dx = max(x1 - x, 0.0, x - x2)\n    dy = max(y1 - y, 0.0, y - y2)\n    return math.hypot(dx, dy)\n\n\ndef point_in_polygon(point: Sequence[float], polygon: Optional[Sequence[Sequence[float]]]) -> bool:\n    if not polygon:\n        return True\n    x, y = map(float, point)\n    inside = False\n    n = len(polygon)\n    j = n - 1\n    for i in range(n):\n        xi, yi = map(float, polygon[i])\n        xj, yj = map(float, polygon[j])\n        crosses = ((yi > y) != (yj > y))\n        if crosses:\n            x_intersect = (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi\n            if x < x_intersect:\n                inside = not inside\n        j = i\n    return inside\n\n\n# ---------------------------------------------------------------------\n# Rolling quality gate\n# ---------------------------------------------------------------------\n\ndef _quality_params(class_name: str, cfg: QualityConfig):\n    if class_name == "person":\n        return {\n            "min_duration": cfg.person_min_duration_s,\n            "high_conf": cfg.person_high_conf,\n            "median_conf": cfg.person_median_conf,\n            "rolling_ratio": cfg.person_rolling_high_ratio,\n            "min_rolling_good_ratio": cfg.person_min_rolling_good_ratio,\n            "min_global_high_ratio": cfg.person_min_global_high_ratio,\n        }\n    if class_name == "luggage":\n        return {\n            "min_duration": cfg.luggage_min_duration_s,\n            "high_conf": cfg.luggage_high_conf,\n            "median_conf": cfg.luggage_median_conf,\n            "rolling_ratio": cfg.luggage_rolling_high_ratio,\n            "min_rolling_good_ratio": cfg.luggage_min_rolling_good_ratio,\n            "min_global_high_ratio": cfg.luggage_min_global_high_ratio,\n        }\n    raise ValueError(f"Unsupported class_name={class_name}")\n\n\ndef quality_profile(track_rows: Sequence[dict], cfg: QualityConfig) -> TrackQualityProfile:\n    if not track_rows:\n        raise ValueError("track_rows is empty")\n\n    rows = sorted(track_rows, key=lambda r: float(r["timestamp_s"]))\n    cls = str(rows[0]["class_name"])\n    p = _quality_params(cls, cfg)\n\n    ts = np.asarray([float(r["timestamp_s"]) for r in rows], dtype=np.float64)\n    conf = np.asarray([float(r["confidence"]) for r in rows], dtype=np.float64)\n\n    rolling_good = []\n    left = 0\n    for i, t in enumerate(ts):\n        while left < i and ts[left] < t - cfg.window_s:\n            left += 1\n        c = conf[left:i + 1]\n        good = (\n            len(c) >= cfg.min_samples\n            and float(np.median(c)) >= p["median_conf"]\n            and float(np.mean(c >= p["high_conf"])) >= p["rolling_ratio"]\n        )\n        rolling_good.append(bool(good))\n\n    start_s = float(ts[0])\n    end_s = float(ts[-1])\n    duration_s = max(0.0, end_s - start_s)\n    global_high_ratio = float(np.mean(conf >= p["high_conf"]))\n    rolling_good_ratio = float(np.mean(rolling_good))\n\n    passed = bool(\n        duration_s >= p["min_duration"]\n        and float(np.median(conf)) >= p["median_conf"]\n        and global_high_ratio >= p["min_global_high_ratio"]\n        and rolling_good_ratio >= p["min_rolling_good_ratio"]\n    )\n\n    return TrackQualityProfile(\n        track_id=int(rows[0]["global_track_id"]),\n        class_name=cls,\n        start_s=start_s,\n        end_s=end_s,\n        duration_s=duration_s,\n        observations=len(rows),\n        mean_confidence=float(np.mean(conf)),\n        median_confidence=float(np.median(conf)),\n        high_conf_ratio=global_high_ratio,\n        rolling_good_ratio=rolling_good_ratio,\n        passed=passed,\n    )\n\n\ndef build_quality_report(rows: Sequence[dict], cfg: QualityConfig):\n    tracks = group_tracks(rows)\n    profiles = {}\n    for track_id, rs in tracks.items():\n        profiles[track_id] = quality_profile(rs, cfg)\n    return profiles\n\n\n# ---------------------------------------------------------------------\n# Physical-object stitching for luggage\n# ---------------------------------------------------------------------\n\ndef _stitch_cost(a_rows: Sequence[dict], b_rows: Sequence[dict], cfg: StitchConfig):\n    a_end = a_rows[-1]\n    b_start = b_rows[0]\n    gap = float(b_start["timestamp_s"]) - float(a_end["timestamp_s"])\n    if gap < 0.0 or gap > cfg.max_gap_s:\n        return None\n\n    dist_px = center_distance(a_end["center_xy"], b_start["center_xy"])\n    norm = dist_px / max(\n        bbox_diag(a_end["bbox_xyxy"]),\n        bbox_diag(b_start["bbox_xyxy"]),\n    )\n\n    if dist_px > cfg.max_center_distance_px or norm > cfg.max_normalized_distance:\n        return None\n\n    # Lower is better. Gap and spatial distance both matter.\n    cost = (gap / max(cfg.max_gap_s, 1e-9)) + norm\n    return {\n        "gap_s": gap,\n        "center_distance_px": dist_px,\n        "normalized_distance": norm,\n        "cost": cost,\n    }\n\n\ndef stitch_luggage_tracks(\n    rows: Sequence[dict],\n    quality_profiles: Dict[int, TrackQualityProfile],\n    cfg: StitchConfig,\n) -> List[PhysicalLuggage]:\n    tracks = group_tracks(rows)\n\n    eligible = []\n    for track_id, rs in tracks.items():\n        prof = quality_profiles[track_id]\n        if prof.class_name == "luggage" and prof.passed:\n            eligible.append((track_id, rs))\n    eligible.sort(key=lambda x: float(x[1][0]["timestamp_s"]))\n\n    # Greedy chain construction. Only quality-passed luggage is stitchable.\n    used = set()\n    physical = []\n    counter = 1\n\n    for i, (track_id, rs) in enumerate(eligible):\n        if track_id in used:\n            continue\n\n        chain_ids = [track_id]\n        chain_rows = list(rs)\n        links = []\n        used.add(track_id)\n        current_rows = rs\n\n        while True:\n            best = None\n            for next_id, next_rows in eligible:\n                if next_id in used:\n                    continue\n                info = _stitch_cost(current_rows, next_rows, cfg)\n                if info is None:\n                    continue\n                if best is None or info["cost"] < best[0]:\n                    best = (info["cost"], next_id, next_rows, info)\n\n            if best is None:\n                break\n\n            _, next_id, next_rows, info = best\n            links.append({\n                "from_track_id": int(chain_ids[-1]),\n                "to_track_id": int(next_id),\n                **{k: float(v) for k, v in info.items()},\n            })\n            chain_ids.append(int(next_id))\n            chain_rows.extend(next_rows)\n            chain_rows.sort(key=lambda r: float(r["timestamp_s"]))\n            current_rows = next_rows\n            used.add(next_id)\n\n        physical.append(\n            PhysicalLuggage(\n                physical_id=f"LUG_{counter:04d}",\n                source_track_ids=[int(x) for x in chain_ids],\n                rows=chain_rows,\n                stitch_links=links,\n            )\n        )\n        counter += 1\n\n    return physical\n\n\n# ---------------------------------------------------------------------\n# Stationary detection\n# ---------------------------------------------------------------------\n\ndef stationary_samples(rows: Sequence[dict], cfg: StationaryConfig):\n    rows = sorted(rows, key=lambda r: float(r["timestamp_s"]))\n    ts = np.asarray([float(r["timestamp_s"]) for r in rows], dtype=np.float64)\n    centers = np.asarray([r["center_xy"] for r in rows], dtype=np.float64)\n    boxes = np.asarray([r["bbox_xyxy"] for r in rows], dtype=np.float64)\n\n    result = []\n    left = 0\n\n    for i, t in enumerate(ts):\n        while left < i and ts[left] < t - cfg.window_s:\n            left += 1\n\n        c = centers[left:i + 1]\n        b = boxes[left:i + 1]\n\n        if len(c) < cfg.min_samples:\n            result.append({\n                "timestamp_s": float(t),\n                "is_stationary": False,\n                "spread_norm": None,\n                "net_norm": None,\n            })\n            continue\n\n        med = np.median(c, axis=0)\n        spread_px = float(np.percentile(np.linalg.norm(c - med, axis=1), 90))\n        widths = np.maximum(1.0, b[:, 2] - b[:, 0])\n        heights = np.maximum(1.0, b[:, 3] - b[:, 1])\n        diag = float(np.median(np.sqrt(widths * widths + heights * heights)))\n\n        spread_norm = spread_px / max(diag, 1.0)\n        net_norm = float(np.linalg.norm(c[-1] - c[0])) / max(diag, 1.0)\n\n        is_stationary = (\n            spread_norm <= cfg.max_spread_norm\n            and net_norm <= cfg.max_net_displacement_norm\n        )\n\n        result.append({\n            "timestamp_s": float(t),\n            "is_stationary": bool(is_stationary),\n            "spread_norm": float(spread_norm),\n            "net_norm": float(net_norm),\n        })\n\n    return result\n\n\ndef find_stationary_runs(rows: Sequence[dict], cfg: StationaryConfig) -> List[StationaryRun]:\n    samples = stationary_samples(rows, cfg)\n    runs = []\n    start_idx = None\n\n    for i, s in enumerate(samples):\n        if s["is_stationary"] and start_idx is None:\n            start_idx = i\n\n        ended = (not s["is_stationary"]) or (i == len(samples) - 1)\n\n        if start_idx is not None and ended:\n            end_idx = i - 1 if not s["is_stationary"] else i\n            start_s = float(samples[start_idx]["timestamp_s"])\n            end_s = float(samples[end_idx]["timestamp_s"])\n            duration = max(0.0, end_s - start_s)\n\n            if duration >= cfg.hold_s:\n                runs.append(\n                    StationaryRun(\n                        start_s=start_s,\n                        end_s=end_s,\n                        confirmed_at_s=start_s + cfg.hold_s,\n                        duration_s=duration,\n                        start_index=start_idx,\n                        end_index=end_idx,\n                    )\n                )\n            start_idx = None\n\n    return runs\n\n\n# ---------------------------------------------------------------------\n# Owner association\n# ---------------------------------------------------------------------\n\ndef associate_owner(\n    physical: PhysicalLuggage,\n    stationary_run: StationaryRun,\n    person_tracks: Dict[int, List[dict]],\n    quality_profiles: Dict[int, TrackQualityProfile],\n    cfg: OwnerConfig,\n    fps_hint: float = 30.0,\n) -> OwnerAssociation:\n    # Use bag history up to the start of the long stationary run.\n    bag_rows = [\n        r for r in physical.rows\n        if float(r["timestamp_s"]) <= stationary_run.start_s\n    ]\n    bag_by_frame = {int(r["frame_index"]): r for r in bag_rows}\n\n    best = None\n\n    for person_id, prs in person_tracks.items():\n        prof = quality_profiles.get(person_id)\n        if prof is None or not prof.passed or prof.class_name != "person":\n            continue\n\n        person_by_frame = {int(r["frame_index"]): r for r in prs}\n        distances = []\n\n        for frame_idx, bag_r in bag_by_frame.items():\n            person_r = person_by_frame.get(frame_idx)\n            if person_r is None:\n                continue\n            d = point_to_bbox_distance(\n                bag_r["center_xy"],\n                person_r["bbox_xyxy"],\n            )\n            d_norm = d / bbox_diag(person_r["bbox_xyxy"])\n            distances.append(float(d_norm))\n\n        if not distances:\n            continue\n\n        overlap_frames = len(distances)\n        overlap_s = overlap_frames / max(fps_hint, 1e-9)\n        if overlap_s < cfg.min_overlap_s:\n            continue\n\n        arr = np.asarray(distances, dtype=np.float64)\n        inside_ratio = float(np.mean(arr <= 1e-9))\n        near_ratio = float(np.mean(arr <= cfg.near_norm))\n        overlap_term = min(overlap_s / 3.0, 1.0)\n\n        score = (\n            0.65 * inside_ratio\n            + 0.25 * near_ratio\n            + 0.10 * overlap_term\n        )\n\n        item = {\n            "person_track_id": int(person_id),\n            "association_score": float(score),\n            "inside_ratio": inside_ratio,\n            "near_ratio": near_ratio,\n            "overlap_frames": int(overlap_frames),\n            "overlap_s": float(overlap_s),\n        }\n\n        if best is None or item["association_score"] > best["association_score"]:\n            best = item\n\n    if best is None or best["association_score"] < cfg.min_association_score:\n        return OwnerAssociation(\n            physical_id=physical.physical_id,\n            person_track_id=None,\n            association_score=float(best["association_score"]) if best else 0.0,\n            inside_ratio=float(best["inside_ratio"]) if best else 0.0,\n            near_ratio=float(best["near_ratio"]) if best else 0.0,\n            overlap_frames=int(best["overlap_frames"]) if best else 0,\n            overlap_s=float(best["overlap_s"]) if best else 0.0,\n            owner_last_near_s=None,\n        )\n\n    owner_id = int(best["person_track_id"])\n    owner_rows = person_tracks[owner_id]\n    owner_by_frame = {int(r["frame_index"]): r for r in owner_rows}\n\n    last_near = None\n    for bag_r in physical.rows:\n        person_r = owner_by_frame.get(int(bag_r["frame_index"]))\n        if person_r is None:\n            continue\n        d = point_to_bbox_distance(\n            bag_r["center_xy"],\n            person_r["bbox_xyxy"],\n        )\n        d_norm = d / bbox_diag(person_r["bbox_xyxy"])\n        if d_norm <= cfg.near_norm:\n            last_near = float(bag_r["timestamp_s"])\n\n    return OwnerAssociation(\n        physical_id=physical.physical_id,\n        person_track_id=owner_id,\n        association_score=float(best["association_score"]),\n        inside_ratio=float(best["inside_ratio"]),\n        near_ratio=float(best["near_ratio"]),\n        overlap_frames=int(best["overlap_frames"]),\n        overlap_s=float(best["overlap_s"]),\n        owner_last_near_s=last_near,\n    )\n\n\n# ---------------------------------------------------------------------\n# Event engine\n# ---------------------------------------------------------------------\n\ndef nearest_row_at_or_after(rows: Sequence[dict], timestamp_s: float) -> Optional[dict]:\n    for r in rows:\n        if float(r["timestamp_s"]) >= timestamp_s:\n            return r\n    return None\n\n\ndef infer_phase7c(\n    rows: Sequence[dict],\n    cfg: Phase7CConfig,\n    fps_hint: float = 30.0,\n):\n    tracks = group_tracks(rows)\n    quality = build_quality_report(rows, cfg.quality)\n\n    person_tracks = {\n        tid: rs for tid, rs in tracks.items()\n        if rs and rs[0]["class_name"] == "person"\n    }\n\n    physical_luggage = stitch_luggage_tracks(rows, quality, cfg.stitch)\n\n    events: List[AbandonedCandidate] = []\n    physical_reports = []\n    owner_reports = []\n    timeline_rows = []\n\n    event_counter = 1\n\n    for physical in physical_luggage:\n        stationary_runs = find_stationary_runs(physical.rows, cfg.stationary)\n\n        physical_report = {\n            "physical_id": physical.physical_id,\n            "source_track_ids": physical.source_track_ids,\n            "start_s": float(physical.rows[0]["timestamp_s"]),\n            "end_s": float(physical.rows[-1]["timestamp_s"]),\n            "duration_s": float(\n                float(physical.rows[-1]["timestamp_s"])\n                - float(physical.rows[0]["timestamp_s"])\n            ),\n            "stitch_links": physical.stitch_links,\n            "stationary_runs": [asdict(r) for r in stationary_runs],\n        }\n        physical_reports.append(physical_report)\n\n        # Build sample-wise stationary flag for timeline.\n        stat_samples = stationary_samples(physical.rows, cfg.stationary)\n\n        chosen_owner = None\n        chosen_run = None\n        chosen_event = None\n\n        for run in stationary_runs:\n            # Final event location must be inside ROI if an ROI is configured.\n            row_for_roi = nearest_row_at_or_after(physical.rows, run.confirmed_at_s)\n            if row_for_roi is None:\n                continue\n            x1, y1, x2, y2 = map(float, row_for_roi["bbox_xyxy"])\n            bottom_center = ((x1 + x2) / 2.0, y2)\n            if not point_in_polygon(bottom_center, cfg.roi_polygon):\n                continue\n\n            owner = associate_owner(\n                physical,\n                run,\n                person_tracks,\n                quality,\n                cfg.owner,\n                fps_hint=fps_hint,\n            )\n            owner_reports.append(asdict(owner))\n\n            if owner.person_track_id is None or owner.owner_last_near_s is None:\n                continue\n\n            candidate_time = max(\n                run.confirmed_at_s,\n                float(owner.owner_last_near_s) + cfg.owner.away_hold_s,\n            )\n\n            # The luggage must remain in the SAME stationary run until candidate time.\n            if candidate_time > run.end_s:\n                continue\n\n            event_row = nearest_row_at_or_after(physical.rows, candidate_time)\n            if event_row is None:\n                continue\n            if float(event_row["timestamp_s"]) > run.end_s + 1e-6:\n                continue\n\n            chosen_owner = owner\n            chosen_run = run\n            chosen_event = AbandonedCandidate(\n                event_id=f"AO_{event_counter:04d}",\n                physical_id=physical.physical_id,\n                source_track_ids=physical.source_track_ids,\n                owner_person_track_id=int(owner.person_track_id),\n                stationary_start_s=float(run.start_s),\n                stationary_confirmed_s=float(run.confirmed_at_s),\n                owner_last_near_s=float(owner.owner_last_near_s),\n                candidate_time_s=float(event_row["timestamp_s"]),\n                owner_away_s=float(\n                    float(event_row["timestamp_s"]) - float(owner.owner_last_near_s)\n                ),\n                association_score=float(owner.association_score),\n                bbox_xyxy=[float(v) for v in event_row["bbox_xyxy"]],\n                center_xy=[float(v) for v in event_row["center_xy"]],\n            )\n            events.append(chosen_event)\n            event_counter += 1\n            break\n\n        # Timeline state\n        current_stat_start = None\n        for row, sample in zip(physical.rows, stat_samples):\n            t = float(row["timestamp_s"])\n            if sample["is_stationary"]:\n                if current_stat_start is None:\n                    current_stat_start = t\n            else:\n                current_stat_start = None\n\n            state = "MOVING"\n            if sample["is_stationary"]:\n                state = "STATIONARY_PENDING"\n                if (\n                    current_stat_start is not None\n                    and t - current_stat_start >= cfg.stationary.hold_s\n                ):\n                    state = "STATIONARY"\n\n            if chosen_owner and chosen_owner.owner_last_near_s is not None:\n                if t >= float(chosen_owner.owner_last_near_s) + cfg.owner.away_hold_s:\n                    if state == "STATIONARY":\n                        state = "OWNER_AWAY"\n\n            if chosen_event and t >= chosen_event.candidate_time_s:\n                state = "ABANDONED_OBJECT_CANDIDATE"\n\n            timeline_rows.append({\n                "frame_index": int(row["frame_index"]),\n                "timestamp_s": t,\n                "physical_id": physical.physical_id,\n                "source_track_id": int(row["global_track_id"]),\n                "bbox_xyxy": [float(v) for v in row["bbox_xyxy"]],\n                "center_xy": [float(v) for v in row["center_xy"]],\n                "confidence": float(row["confidence"]),\n                "state": state,\n                "owner_person_track_id": (\n                    int(chosen_owner.person_track_id)\n                    if chosen_owner and chosen_owner.person_track_id is not None\n                    else None\n                ),\n                "stationary_spread_norm": sample["spread_norm"],\n                "stationary_net_norm": sample["net_norm"],\n            })\n\n    quality_report = {\n        str(tid): asdict(profile)\n        for tid, profile in sorted(quality.items())\n    }\n\n    summary = {\n        "input_rows": len(rows),\n        "input_tracks": len(tracks),\n        "quality_pass_person_tracks": sum(\n            1 for p in quality.values()\n            if p.class_name == "person" and p.passed\n        ),\n        "quality_pass_luggage_tracks": sum(\n            1 for p in quality.values()\n            if p.class_name == "luggage" and p.passed\n        ),\n        "physical_luggage_objects": len(physical_luggage),\n        "stitch_links": sum(len(p.stitch_links) for p in physical_luggage),\n        "owner_associations_attempted": len(owner_reports),\n        "abandoned_candidates": len(events),\n    }\n\n    return {\n        "summary": summary,\n        "quality_report": quality_report,\n        "physical_luggage": physical_reports,\n        "owner_associations": owner_reports,\n        "events": [asdict(e) for e in events],\n        "timeline": timeline_rows,\n    }\n\n\n# ---------------------------------------------------------------------\n# Visualization\n# ---------------------------------------------------------------------\n\ndef annotate_video(\n    video_path: str | Path,\n    source_rows: Sequence[dict],\n    result: dict,\n    output_path: str | Path,\n):\n    import cv2\n\n    video_path = str(video_path)\n    output_path = str(output_path)\n\n    cap = cv2.VideoCapture(video_path)\n    if not cap.isOpened():\n        raise RuntimeError(f"Could not open video: {video_path}")\n\n    fps = float(cap.get(cv2.CAP_PROP_FPS))\n    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))\n    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))\n\n    writer = cv2.VideoWriter(\n        output_path,\n        cv2.VideoWriter_fourcc(*"mp4v"),\n        fps if fps > 0 else 30.0,\n        (width, height),\n    )\n    if not writer.isOpened():\n        raise RuntimeError(f"Could not create output: {output_path}")\n\n    timeline_by_frame = defaultdict(list)\n    for row in result["timeline"]:\n        timeline_by_frame[int(row["frame_index"])].append(row)\n\n    # Only quality-passed persons are useful for owner display.\n    quality = result["quality_report"]\n    person_by_frame = defaultdict(list)\n    for r in source_rows:\n        if r["class_name"] != "person":\n            continue\n        q = quality.get(str(int(r["global_track_id"])))\n        if q and q["passed"]:\n            person_by_frame[int(r["frame_index"])].append(r)\n\n    event_by_physical = {\n        e["physical_id"]: e for e in result["events"]\n    }\n\n    frame_idx = 0\n    while True:\n        ok, frame = cap.read()\n        if not ok:\n            break\n\n        # Persons: subdued owner/context boxes.\n        for p in person_by_frame.get(frame_idx, []):\n            x1, y1, x2, y2 = map(int, p["bbox_xyxy"])\n            cv2.rectangle(frame, (x1, y1), (x2, y2), (120, 200, 120), 1)\n            cv2.putText(\n                frame,\n                f"P {int(p[\'global_track_id\'])}",\n                (x1, max(16, y1 - 5)),\n                cv2.FONT_HERSHEY_SIMPLEX,\n                0.4,\n                (120, 200, 120),\n                1,\n                cv2.LINE_AA,\n            )\n\n        for item in timeline_by_frame.get(frame_idx, []):\n            x1, y1, x2, y2 = map(int, item["bbox_xyxy"])\n            state = item["state"]\n\n            if state == "MOVING":\n                color = (180, 180, 180)\n            elif state == "STATIONARY_PENDING":\n                color = (0, 200, 255)\n            elif state == "STATIONARY":\n                color = (0, 165, 255)\n            elif state == "OWNER_AWAY":\n                color = (0, 100, 255)\n            else:\n                color = (0, 0, 255)\n\n            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)\n            label = f"{item[\'physical_id\']} {state}"\n            if item["owner_person_track_id"] is not None:\n                label += f" owner={item[\'owner_person_track_id\']}"\n            cv2.putText(\n                frame,\n                label,\n                (x1, max(18, y1 - 6)),\n                cv2.FONT_HERSHEY_SIMPLEX,\n                0.45,\n                color,\n                1,\n                cv2.LINE_AA,\n            )\n\n        # Persistent banner once an event has fired.\n        active_events = [\n            e for e in result["events"]\n            if frame_idx / max(fps, 1e-9) >= e["candidate_time_s"]\n        ]\n        if active_events:\n            e = active_events[-1]\n            cv2.rectangle(frame, (0, 0), (width, 38), (0, 0, 180), -1)\n            cv2.putText(\n                frame,\n                (\n                    f"ABANDONED OBJECT CANDIDATE {e[\'event_id\']} "\n                    f"owner={e[\'owner_person_track_id\']}"\n                ),\n                (10, 25),\n                cv2.FONT_HERSHEY_SIMPLEX,\n                0.65,\n                (255, 255, 255),\n                2,\n                cv2.LINE_AA,\n            )\n\n        writer.write(frame)\n        frame_idx += 1\n\n    cap.release()\n    writer.release()\n'  # materialized below by generated bundle


def find_one(pattern, explicit_env=None):
    if explicit_env:
        p = Path(explicit_env)
        if not p.is_file():
            raise FileNotFoundError(p)
        return p
    items = list(INPUT.rglob(pattern))
    if len(items) != 1:
        raise RuntimeError(
            f"Need exactly one {pattern} or set explicit env. Found:\n"
            + "\n".join(map(str, items[:30]))
        )
    return items[0]


def parse_roi():
    text = os.environ.get("ROI_POLYGON_JSON", "").strip()
    if not text:
        return None
    pts = json.loads(text)
    if not isinstance(pts, list) or len(pts) < 3:
        raise ValueError("ROI_POLYGON_JSON must be [[x,y], ...] with >=3 points")
    return [(float(x), float(y)) for x, y in pts]


def main():
    # Lightweight dependencies only.
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "numpy", "opencv-python-headless"],
        check=True,
    )

    core_path = WORK / "phase7c_core.py"
    core_path.write_text(EMBEDDED_CORE, encoding="utf-8")
    sys.path.insert(0, str(WORK))

    from phase7c_core import (
        load_jsonl,
        Phase7CConfig,
        QualityConfig,
        StitchConfig,
        StationaryConfig,
        OwnerConfig,
        infer_phase7c,
        annotate_video,
    )

    tracks_path = find_one(
        "tracks_v4.jsonl",
        os.environ.get("TRACKS_V4_PATH"),
    )

    video_env = os.environ.get("VIDEO_PATH")
    video_path = (
        Path(video_env)
        if video_env
        else find_one("aboda-video1.avi")
    )
    if video_path is not None and not video_path.is_file():
        raise FileNotFoundError(video_path)

    rows = load_jsonl(tracks_path)

    fps_hint = float(os.environ.get("FPS_HINT", "29.97"))
    if video_path is not None:
        import cv2
        cap = cv2.VideoCapture(str(video_path))
        if cap.isOpened():
            fps_read = float(cap.get(cv2.CAP_PROP_FPS))
            if fps_read > 0:
                fps_hint = fps_read
        cap.release()

    cfg = Phase7CConfig(
        quality=QualityConfig(
            window_s=float(os.environ.get("QUALITY_WINDOW_S", "2.0")),
            person_min_duration_s=float(os.environ.get("PERSON_MIN_DURATION_S", "0.7")),
            person_high_conf=float(os.environ.get("PERSON_HIGH_CONF", "0.40")),
            person_median_conf=float(os.environ.get("PERSON_MEDIAN_CONF", "0.40")),
            person_rolling_high_ratio=float(os.environ.get("PERSON_ROLLING_HIGH_RATIO", "0.30")),
            person_min_rolling_good_ratio=float(os.environ.get("PERSON_MIN_ROLLING_GOOD_RATIO", "0.50")),
            person_min_global_high_ratio=float(os.environ.get("PERSON_MIN_GLOBAL_HIGH_RATIO", "0.30")),
            luggage_min_duration_s=float(os.environ.get("LUGGAGE_MIN_DURATION_S", "1.5")),
            luggage_high_conf=float(os.environ.get("LUGGAGE_HIGH_CONF", "0.35")),
            luggage_median_conf=float(os.environ.get("LUGGAGE_MEDIAN_CONF", "0.35")),
            luggage_rolling_high_ratio=float(os.environ.get("LUGGAGE_ROLLING_HIGH_RATIO", "0.50")),
            luggage_min_rolling_good_ratio=float(os.environ.get("LUGGAGE_MIN_ROLLING_GOOD_RATIO", "0.50")),
            luggage_min_global_high_ratio=float(os.environ.get("LUGGAGE_MIN_GLOBAL_HIGH_RATIO", "0.50")),
        ),
        stitch=StitchConfig(
            max_gap_s=float(os.environ.get("STITCH_MAX_GAP_S", "0.80")),
            max_center_distance_px=float(os.environ.get("STITCH_MAX_CENTER_PX", "80")),
            max_normalized_distance=float(os.environ.get("STITCH_MAX_NORM", "1.20")),
        ),
        stationary=StationaryConfig(
            window_s=float(os.environ.get("STATIONARY_WINDOW_S", "2.0")),
            min_samples=int(os.environ.get("STATIONARY_MIN_SAMPLES", "10")),
            max_spread_norm=float(os.environ.get("STATIONARY_MAX_SPREAD_NORM", "0.15")),
            max_net_displacement_norm=float(os.environ.get("STATIONARY_MAX_NET_NORM", "0.20")),
            hold_s=float(os.environ.get("STATIONARY_HOLD_S", "3.0")),
        ),
        owner=OwnerConfig(
            near_norm=float(os.environ.get("OWNER_NEAR_NORM", "0.50")),
            min_overlap_s=float(os.environ.get("OWNER_MIN_OVERLAP_S", "0.70")),
            min_association_score=float(os.environ.get("OWNER_MIN_SCORE", "0.60")),
            away_hold_s=float(os.environ.get("OWNER_AWAY_HOLD_S", "5.0")),
        ),
        roi_polygon=parse_roi(),
    )

    result = infer_phase7c(rows, cfg, fps_hint=fps_hint)

    OUT.mkdir(parents=True, exist_ok=True)

    files = {
        "phase7c_summary.json": result["summary"],
        "quality_report.json": result["quality_report"],
        "physical_luggage.json": result["physical_luggage"],
        "owner_associations.json": result["owner_associations"],
        "phase7c_events.json": result["events"],
    }
    for name, payload in files.items():
        (OUT / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    with (OUT / "phase7c_timeline.jsonl").open("w", encoding="utf-8") as f:
        for row in result["timeline"]:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    if video_path is not None:
        annotate_video(
            video_path,
            rows,
            result,
            OUT / "annotated_phase7c.mp4",
        )

    print("=" * 100)
    print("PHASE 7C v1 COMPLETE")
    print("=" * 100)
    print(json.dumps(result["summary"], indent=2))
    print("\nEVENTS")
    print(json.dumps(result["events"], indent=2))
    print("\nOutputs:", OUT)
    print("=" * 100)


if __name__ == "__main__":
    main()
