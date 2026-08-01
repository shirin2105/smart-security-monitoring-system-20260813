import pytest
from app.cv.worker import CVWorker


def test_cv_worker_intrusion_pipeline():
    worker = CVWorker(camera_id="cam_01")
    candidates = worker.run(max_frames=10)
    assert isinstance(candidates, list)
