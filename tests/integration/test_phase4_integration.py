import pytest
from app.cv.worker import CVWorker


def test_phase4_cv_worker_with_all_engines():
    worker = CVWorker(camera_id="cam_01")
    candidates = worker.run(max_frames=10)
    assert isinstance(candidates, list)
    assert len(worker.engines) == 3
    assert worker.abandoned_engine.temporal_enabled is True
    assert worker.abandoned_engine.temporal_max_dimension == 480
