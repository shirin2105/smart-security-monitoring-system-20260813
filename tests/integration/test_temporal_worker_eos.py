import pytest

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
def test_worker_finalizes_temporal_state_on_eos_and_stream_error(error):
    worker = CVWorker(camera_id="cam_01")
    source = EmptySource(error)
    finalizer = FinalizeSpy()
    worker.source = source
    worker.abandoned_engine = finalizer

    if error:
        with pytest.raises(RuntimeError, match="stream failed"):
            worker.run()
    else:
        assert worker.run() == []

    assert finalizer.calls == 1
    assert source.released is True


def test_worker_receives_production_temporal_resource_defaults():
    worker = CVWorker(camera_id="cam_01")
    engine = worker.abandoned_engine
    assert engine.temporal_enabled is True
    assert engine.temporal_pre_seconds == 8
    assert engine.temporal_post_seconds == 8
    assert engine.temporal_sample_fps == 1
    assert engine.temporal_max_frames == 17
    assert engine.temporal_max_dimension == 480
    assert engine.temporal_buffer_byte_ceiling == 12_000_000
