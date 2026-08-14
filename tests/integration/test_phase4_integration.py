import pytest
from types import SimpleNamespace
from app.cv.worker import CVWorker
from app.cv.events.phase7c_abandoned_adapter import Phase7CAbandonedAdapter


def test_phase4_cv_worker_with_all_engines(empty_detector):
    worker = CVWorker(camera_id="cam_01", detector=empty_detector,
                      tracker=SimpleNamespace(track=lambda _detections, _frame: []))
    candidates = worker.run(max_frames=10)
    assert isinstance(candidates, list)
    assert len(worker.adapters) == 3
    assert isinstance(worker.adapters[-1], Phase7CAbandonedAdapter)
