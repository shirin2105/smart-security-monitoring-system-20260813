import json
from unittest.mock import patch

from app.common.schemas import FrameData
from app.cv.events.phase7c_abandoned_adapter import Phase7CAbandonedAdapter
from app.cv.track_store import TrackState


def _frame(frame_id: int = 1) -> FrameData:
    return FrameData(
        camera_id="clip-1", frame_id=frame_id, captured_at="2026-01-01T00:00:10Z",
        source_type="VIDEO", source_fps=5, inference_fps=5,
    )


def _bag(timestamp: str = "2026-01-01T00:00:10Z") -> TrackState:
    return TrackState(7, "luggage", [20, 20, 30, 30], 0.8, timestamp)


def test_phase11b_trace_is_not_created_when_debug_is_disabled(tmp_path):
    adapter = Phase7CAbandonedAdapter(
        "clip-1", {"debug": {"enabled": False, "trace_output_dir": str(tmp_path)}}, fps_hint=5,
    )

    adapter.evaluate([_bag()], _frame())

    assert not list(tmp_path.glob("*.jsonl"))
    assert adapter._physical_counter == 0
    assert adapter._physical_ids == []


def test_phase11b_trace_emits_one_schema_row_per_physical_luggage_frame(tmp_path):
    adapter = Phase7CAbandonedAdapter(
        "clip-1",
        {"debug": {"enabled": True, "emit_trace_jsonl": True, "trace_output_dir": str(tmp_path)}},
        fps_hint=5,
    )

    adapter.evaluate([_bag()], _frame())
    adapter.evaluate([_bag()], _frame())

    trace_path = tmp_path / "clip-1.jsonl"
    rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    row = rows[0]
    assert row["physical_luggage_id"] == "LUG_0001"
    assert row["source_track_ids"] == [7]
    assert row["candidate_state"] == "QUALITY_REJECTED"
    assert row["failure_hint"] == "QUALITY_REJECT"
    assert row["event_emitted"] is False


def test_event_emission_uses_source_tracks_when_diagnostic_ids_diverge(tmp_path):
    adapter = Phase7CAbandonedAdapter(
        "clip-1",
        {"debug": {"enabled": True, "emit_trace_jsonl": True, "trace_output_dir": str(tmp_path)}},
        fps_hint=5,
    )
    no_event = {"quality_report": {"7": {"passed": False, "rolling_good_ratio": 0.0}},
                "physical_luggage": [], "owner_associations": [], "events": []}
    event = {
        "quality_report": {"9": {"passed": True, "rolling_good_ratio": 1.0}},
        "physical_luggage": [{"physical_id": "core-1", "source_track_ids": [9],
                               "stationary_runs": [{"duration_s": 8.0}]}],
        "owner_associations": [{"physical_id": "core-1", "person_track_id": 3,
                                "association_score": 0.8, "owner_last_near_s": 2.0,
                                "selection_reason": "highest_association_score",
                                "rejection_reason": None,
                                "history_window_start_s": 0.0,
                                "history_window_end_s": 2.0,
                                "candidates": [{"person_track_id": 3,
                                                "candidate_bboxes": [[1, 2, 3, 4]],
                                                "min_distance_norm": 0.0,
                                                "association_score": 0.8,
                                                "first_seen_s": 0.0,
                                                "last_seen_s": 2.0,
                                                "track_age_s": 2.0}]}],
        "events": [{"source_track_ids": [9], "owner_person_track_id": 3,
                    "association_score": 0.8, "stationary_start_s": 2.0,
                    "owner_last_near_s": 4.0}],
    }
    second_frame = _frame(2).model_copy(update={"captured_at": "2026-01-01T00:00:11Z"})
    with patch("app.cv.events.phase7c_abandoned_adapter.infer_phase7c", side_effect=[no_event, event]):
        adapter.evaluate([_bag()], _frame())
        adapter.evaluate([TrackState(9, "luggage", [20, 20, 30, 30], 0.8,
                                           second_frame.captured_at)], second_frame)

    rows = [json.loads(line) for line in (tmp_path / "clip-1.jsonl").read_text().splitlines()]
    assert rows[0]["physical_luggage_id"] == "LUG_0001"
    assert rows[0]["event_emitted"] is False
    assert rows[1]["physical_luggage_id"] == "LUG_0002"
    assert rows[1]["event_emitted"] is True
    assert rows[1]["owner_candidate_person_ids"] == [3]
    assert rows[1]["selected_owner_person_id"] == 3
    assert rows[1]["owner_selection_reason"] == "highest_association_score"
    assert rows[1]["owner_eventually_associated"] is True
