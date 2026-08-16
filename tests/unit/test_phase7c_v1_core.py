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
        diagnostics_enabled=True,
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


def brief_close_placement_with_long_owner_track():
    rows = []
    for frame in range(50):
        bag_center = (100 + frame, 170)
        owner_center = (bag_center[0], 150) if frame >= 45 else (bag_center[0], 70)
        rows.append(row(frame, "person", 1_000_010, owner_center, size=(60, 100)))
        rows.append(row(frame, "luggage", 2_000_010, bag_center, size=(24, 30)))
        rows.append(row(frame, "person", 1_000_011, (300, 80), size=(40, 80)))
    for frame in range(53, 150):
        rows.append(row(frame, "luggage", 2_000_011, (149, 170), size=(28, 34)))
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


def test_roi_no_longer_excludes_stationary_luggage():
    # Product Policy v2: ABANDONED_OBJECT is full-frame; a valid-floor ROI must
    # not suppress a genuine abandonment candidate.
    roi = [(0, 0), (80, 0), (80, 100), (0, 100)]
    result = infer_phase7c(
        carried_then_stationary(owner_stays_until=49),
        compact_config(roi),
        fps_hint=10,
    )
    assert result["summary"]["abandoned_candidates"] == 1


def test_one_physical_luggage_emits_at_most_one_candidate():
    result = infer_phase7c(
        carried_then_stationary(owner_stays_until=49), compact_config(), fps_hint=10
    )
    assert result["summary"]["physical_luggage_objects"] == 1
    assert len(result["events"]) == 1
    assert result["events"][0]["source_track_ids"] == [2_000_001, 2_000_002]


def test_owner_report_records_candidates_and_explicit_rejection_reason():
    rows = carried_then_stationary(owner_stays_until=49)
    result = infer_phase7c(rows, compact_config(), fps_hint=10)

    report = result["owner_associations"][0]
    assert report["rejection_reason"] is None
    assert report["history_window_start_s"] < report["history_window_end_s"]
    candidate = report["candidates"][0]
    assert candidate["person_track_id"] == 1_000_001
    assert candidate["first_seen_s"] == 0.0
    assert candidate["last_seen_s"] == 4.9
    assert candidate["min_distance_norm"] == 0.0
    assert candidate["association_score"] >= 0.6
    assert candidate["min_distance_px"] == 0.0
    assert candidate["temporal_overlap_ratio"] > 0.0
    assert candidate["overlap_term"] > 0.0
    assert candidate["inside_score_component"] >= 0.0
    assert candidate["proximity_score_component"] >= 0.0
    assert candidate["near_score_component"] >= 0.0
    assert candidate["overlap_score_component"] >= 0.0
    assert candidate["min_association_score"] == 0.6
    assert candidate["candidate_eligible"] is True
    assert candidate["candidate_selected"] is True
    assert candidate["candidate_present_before_stationary"] is True
    assert candidate["candidate_present_at_stationary"] is False
    assert candidate["candidate_present_after_stationary"] is False
    assert candidate["person_track_fragmented"] is False


def test_owner_report_explains_score_below_threshold():
    rows = carried_then_stationary(owner_stays_until=-1)
    for frame in range(50):
        rows.append(row(frame, "person", 1_000_003, (100 + frame, 140), size=(30, 30)))
    result = infer_phase7c(rows, compact_config(), fps_hint=10)

    report = result["owner_associations"][0]
    assert report["person_track_id"] is None
    assert report["rejection_reason"] == "CANDIDATE_SCORE_BELOW_THRESHOLD"
    assert report["candidates"][0]["near_ratio"] > 0


def test_brief_close_placement_reproduces_score_below_threshold():
    result = infer_phase7c(
        brief_close_placement_with_long_owner_track(), compact_config(), fps_hint=10
    )

    report = result["owner_associations"][0]
    assert report["person_track_id"] is None
    assert report["association_score"] < 0.6
    assert report["rejection_reason"] == "CANDIDATE_SCORE_BELOW_THRESHOLD"
    assert result["summary"]["abandoned_candidates"] == 0
    assert report["candidates"][1]["candidate_selected"] is False


def test_diagnostics_flag_is_event_and_score_neutral():
    rows = carried_then_stationary(owner_stays_until=49)
    enabled = infer_phase7c(rows, compact_config(), fps_hint=10)
    disabled_cfg = compact_config()
    disabled_cfg.diagnostics_enabled = False
    disabled = infer_phase7c(rows, disabled_cfg, fps_hint=10)

    assert enabled["events"] == disabled["events"]
    assert enabled["owner_associations"][0]["association_score"] == disabled["owner_associations"][0]["association_score"]
    assert "proximity_score_component" not in disabled["owner_associations"][0]["candidates"][0]


def test_owner_precheck_full_frame_ignores_roi():
    # Product Policy v2: abandoned is full-frame, so the precheck must never reject
    # on ROI grounds; association is still attempted.
    rows = carried_then_stationary(owner_stays_until=49)
    cfg = compact_config()
    cfg.roi_polygon = [[0, 0], [50, 0], [50, 50], [0, 50]]

    result = infer_phase7c(rows, cfg, fps_hint=10)

    assert result["owner_associations"]
    assert result["owner_prechecks"][0]["eligible"] is True
    assert result["owner_prechecks"][0]["rejection_reason"] is None
