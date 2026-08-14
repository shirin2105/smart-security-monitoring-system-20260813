import pytest
from types import SimpleNamespace

from app.cv.worker import CVWorker


class EmptySource:
    def __init__(self, error=None):
        self.error = error
        self.released = False

    def read_frames(self):
        if self.error:
            raise self.error
        return iter(())

    def release(self):
        self.released = True


class FinalizeSpy:
    def __init__(self):
        self.calls = 0

    def finalize(self):
        self.calls += 1
        return []


@pytest.mark.parametrize("error", [None, RuntimeError("stream failed")])
def test_worker_finalizes_temporal_state_on_eos_and_stream_error(error, empty_detector):
    worker = CVWorker(camera_id="cam_01", detector=empty_detector,
                      tracker=SimpleNamespace(track=lambda _detections, _frame: []))
    source = EmptySource(error)
    finalizer = FinalizeSpy()
    worker.source = source
    worker.adapters = (finalizer,)

    if error:
        with pytest.raises(RuntimeError, match="stream failed"):
            worker.run()
    else:
        assert worker.run() == []

    assert finalizer.calls == 1
    assert source.released is True


def test_worker_uses_phase7c_abandoned_adapter(empty_detector):
    worker = CVWorker(camera_id="cam_01", detector=empty_detector,
                      tracker=SimpleNamespace(track=lambda _detections, _frame: []))
    assert worker.adapters[-1].config.stationary.hold_s == 3.0
    assert worker.adapters[-1].config.owner.away_hold_s == 5.0
