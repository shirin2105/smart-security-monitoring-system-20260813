from __future__ import annotations

import sys
from pathlib import Path


CORE_DIR = Path(__file__).resolve().parents[2] / "kaggle_pipeline" / "phase7c_kernel"
sys.path.insert(0, str(CORE_DIR))

from phase7c_core import OwnerConfig, Phase7CConfig, StationaryConfig, infer_phase7c


def row(frame, cls, track_id, center, confidence=0.9, size=(30, 40), fps=10):
    cx, cy = center
    width, height = size
    return {
        "frame_index": frame,
        "timestamp_s": frame / fps,
        "class_id": 0 if cls == "person" else 1,
        "class_name": cls,
        "global_track_id": track_id,
        "local_track_id": track_id % 1_000_000,
        "bbox_xyxy": [
            cx - width / 2,
            cy - height / 2,
            cx + width / 2,
            cy + height / 2,
        ],
        "center_xy": [cx, cy],
        "confidence": confidence,
    }


def compact_config(roi=None):
    return Phase7CConfig(
        stationary=StationaryConfig(
            window_s=1.0,
            min_samples=5,
            max_spread_norm=0.15,
            max_net_displacement_norm=0.2,
            hold_s=2.0,
        ),
        owner=OwnerConfig(
            near_norm=0.5,
            min_overlap_s=0.7,
            min_association_score=0.6,
            away_hold_s=3.0,
        ),
        roi_polygon=roi,
    )


def carried_then_stationary(owner_stays_until=49, bag_end=150):
    rows = []
    for frame in range(50):
        center = (100 + frame, 150)
        if frame <= owner_stays_until:
            rows.append(row(frame, "person", 1_000_001, center, size=(60, 100)))
        rows.append(
            row(frame, "luggage", 2_000_001, (center[0], 170), size=(24, 30))
        )
    for frame in range(53, bag_end):
        if frame <= owner_stays_until:
            rows.append(row(frame, "person", 1_000_001, (149, 150), size=(60, 100)))
        rows.append(row(frame, "luggage", 2_000_002, (149, 170), size=(28, 34)))
    return rows


def test_owner_remaining_near_bag_blocks_candidate():
    result = infer_phase7c(
        carried_then_stationary(owner_stays_until=149), compact_config(), fps_hint=10
    )
    assert result["summary"]["abandoned_candidates"] == 0


def test_owner_return_before_away_dwell_blocks_candidate():
    rows = carried_then_stationary(owner_stays_until=49)
    for frame in range(75, 150):
        rows.append(
            row(frame, "person", 1_000_001, (149, 150), size=(60, 100))
        )
    result = infer_phase7c(rows, compact_config(), fps_hint=10)
    assert result["summary"]["abandoned_candidates"] == 0


def test_short_stationary_pause_does_not_emit_candidate():
    result = infer_phase7c(
        carried_then_stationary(owner_stays_until=49, bag_end=67),
        compact_config(),
        fps_hint=10,
    )
    assert result["summary"]["abandoned_candidates"] == 0


def test_roi_excludes_stationary_luggage():
    roi = [(0, 0), (80, 0), (80, 100), (0, 100)]
    result = infer_phase7c(
        carried_then_stationary(owner_stays_until=49),
        compact_config(roi),
        fps_hint=10,
    )
    assert result["summary"]["abandoned_candidates"] == 0


def test_one_physical_luggage_emits_at_most_one_candidate():
    result = infer_phase7c(
        carried_then_stationary(owner_stays_until=49), compact_config(), fps_hint=10
    )
    assert result["summary"]["physical_luggage_objects"] == 1
    assert len(result["events"]) == 1
    assert result["events"][0]["source_track_ids"] == [2_000_001, 2_000_002]
