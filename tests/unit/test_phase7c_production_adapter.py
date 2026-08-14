from unittest.mock import patch

from app.common.schemas import FrameData
from app.cv.events.phase7c_abandoned_adapter import Phase7CAbandonedAdapter
from app.cv.track_store import TrackState


def test_phase7c_adapter_uses_production_core_and_emits_candidate_fact():
    adapter = Phase7CAbandonedAdapter("cam")
    frame = FrameData(camera_id="cam", frame_id=1, captured_at="2026-01-01T00:00:10Z",
                      source_type="VIDEO", source_fps=1, inference_fps=1)
    bag = TrackState(2, "luggage", [20, 20, 30, 30], 0.8, frame.captured_at)
    result = {
        "quality_report": {"2": {"rolling_good_ratio": 0.75}},
        "events": [{"physical_id": "LUG_0001", "source_track_ids": [2],
                    "owner_person_track_id": 1, "association_score": 0.8,
                    "stationary_start_s": 2.0, "owner_last_near_s": 4.0}],
    }
    with patch("app.cv.events.phase7c_abandoned_adapter.infer_phase7c",
               return_value=result) as core:
        signal = adapter.evaluate([bag], frame)[0]
    core.assert_called_once()
    assert signal.active and signal.event_type == "ABANDONED_OBJECT"
    assert signal.evidence["luggage_quality_score"] == 0.75


def test_owner_return_ends_active_candidate():
    adapter = Phase7CAbandonedAdapter("cam")
    frames = [FrameData(camera_id="cam", frame_id=i,
                        captured_at=f"2026-01-01T00:00:{10+i:02d}Z",
                        source_type="VIDEO", source_fps=1, inference_fps=1)
              for i in range(2)]
    bag = TrackState(2, "luggage", [20, 20, 30, 30], 0.8, frames[0].captured_at)
    owner = TrackState(1, "person", [20, 20, 30, 30], 0.9, frames[1].captured_at)
    result = {"quality_report": {}, "events": [{
        "physical_id": "LUG_0001", "source_track_ids": [2],
        "owner_person_track_id": 1, "association_score": 0.8,
        "stationary_start_s": 2.0, "owner_last_near_s": 4.0,
    }]}
    with patch("app.cv.events.phase7c_abandoned_adapter.infer_phase7c",
               return_value=result):
        assert adapter.evaluate([bag], frames[0])[0].active is True
        assert adapter.evaluate([bag, owner], frames[1])[0].active is False
