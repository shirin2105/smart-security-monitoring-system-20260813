from types import SimpleNamespace

from app.common.schemas import FrameData
from app.cv.events.frame_time import frame_time_seconds
from app.cv.frame_sampler import FrameSampler
from app.cv.track_store import TrackStore
from app.cv.worker import CVWorker
from app.sources.camera_health import CameraHealthMonitor


def _live_frame(frame_id: int, captured_at: str) -> FrameData:
    return FrameData(
        camera_id="cam", frame_id=frame_id, captured_at=captured_at, source_type="RTSP", source_fps=0, inference_fps=5
    )


def test_live_sampler_uses_capture_time_when_rtsp_fps_is_invalid():
    sampler = FrameSampler(inference_fps=5)
    frames = [
        _live_frame(1, "2026-08-14T00:00:00.000000Z"),
        _live_frame(2, "2026-08-14T00:00:00.100000Z"),
        _live_frame(3, "2026-08-14T00:00:00.200000Z"),
        _live_frame(4, "2026-08-14T00:00:00.400000Z"),
    ]
    assert [sampler.should_process(frame) for frame in frames] == [True, False, True, True]


def test_file_sampler_preserves_phase9_frame_interval_behavior():
    sampler = FrameSampler(inference_fps=5)
    frames = [
        FrameData(
            camera_id="cam",
            frame_id=index,
            captured_at="2026-01-01T00:00:00Z",
            source_type="SIMULATED",
            source_fps=25,
            inference_fps=5,
        )
        for index in range(1, 11)
    ]
    assert [frame.frame_id for frame in frames if sampler.should_process(frame)] == [5, 10]


def test_long_outage_resets_temporal_components_but_not_detector():
    frame = _live_frame(1, "2026-08-14T00:00:10.000000Z")
    reset_calls = []

    class Source:
        def read_frames(self):
            return iter([frame])

        def release(self):
            pass

        def consume_outage_duration(self):
            return 6.0

    class Resetter:
        def reset(self):
            reset_calls.append(self)

        def track(self, *_):
            return []

        def evaluate(self, *_):
            return []

    worker = CVWorker.__new__(CVWorker)
    worker.camera_id = "cam"
    worker.source = Source()
    worker.reset_after_s = 5.0
    worker.outage_reset_count = 0
    worker.health_monitor = SimpleNamespace(
        update_frame_time=lambda _: None,
        record_processed=lambda _: None,
        record_skipped=lambda: None,
    )
    worker.frame_sampler = SimpleNamespace(should_process=lambda _: True)
    worker.detector = SimpleNamespace(detect=lambda _: ([], 0.0))
    worker.tracker = Resetter()
    worker.track_store = Resetter()
    worker.adapters = (Resetter(),)
    worker.event_manager = SimpleNamespace(end_all=lambda: [], process=lambda _: None)
    worker.publisher = SimpleNamespace(publish=lambda _: True)
    worker.event_id_namespace = lambda value: value

    assert worker.run(max_frames=1) == []
    assert len(reset_calls) == 3
    assert worker.outage_reset_count == 1
    assert worker.event_manager.camera_id == "cam"


def test_track_store_reset_discards_prior_session_tracks():
    store = TrackStore("cam")
    store.tracks[99] = object()
    store.reset()
    assert store.get_active_tracks() == []


def test_live_event_clock_uses_capture_time_not_invalid_fps():
    first = _live_frame(1, "2026-08-14T00:00:02Z")
    second = _live_frame(2, "2026-08-14T00:00:03Z")
    assert frame_time_seconds(second) - frame_time_seconds(first) == 1.0


def test_camera_health_exposes_source_and_processing_metrics():
    source = SimpleNamespace(
        connection_state="RECONNECTING",
        reconnect_count=2,
        consecutive_read_failures=3,
        read_decode_errors=4,
        last_reconnect_at="2026-08-14T00:00:00Z",
        frames_received=10,
        frames_dropped=1,
        source_fps=25.0,
        processed_fps=5.0,
    )
    monitor = CameraHealthMonitor("cam")
    monitor.attach_source(source)
    monitor.record_skipped()
    monitor.record_processed(12.5)
    status = monitor.get_status()
    assert status["connection_state"] == "RECONNECTING"
    assert status["frames_received"] == 10
    assert status["frames_processed"] == 1
    assert status["frames_dropped_skipped"] == 2
    assert status["last_inference_latency_ms"] == 12.5


def test_long_outage_publishes_controlled_end_before_reset():
    order = []
    ending = SimpleNamespace(event_id="event-1", event_state="END")

    class Source:
        def consume_outage_duration(self):
            return 6.0

    class Resetter:
        def reset(self):
            order.append("reset")

    worker = CVWorker.__new__(CVWorker)
    worker.camera_id = "cam"
    worker.source = Source()
    worker.reset_after_s = 5.0
    worker.outage_reset_count = 0
    worker.adapters = (Resetter(),)
    worker.tracker = Resetter()
    worker.track_store = Resetter()
    worker.event_manager = SimpleNamespace(end_all=lambda: [ending])
    worker.event_id_namespace = lambda value: value
    worker._publish = lambda *_: order.append("publish-end")
    generated = []

    worker._reset_after_long_outage(generated)

    assert order == ["publish-end", "reset", "reset", "reset"]
    assert generated == [ending]
    assert worker.outage_reset_count == 1
