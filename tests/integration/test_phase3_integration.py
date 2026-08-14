import pytest
from types import SimpleNamespace
from app.cv.worker import CVWorker


def test_phase3_cv_worker_with_crowd_engine(empty_detector):
    worker = CVWorker(camera_id="cam_02", detector=empty_detector,
                      tracker=SimpleNamespace(track=lambda _detections, _frame: []))
    candidates = worker.run(max_frames=10)
    assert isinstance(candidates, list)
