from types import SimpleNamespace

from app.common.schemas import FrameData
from app.cv.worker import CVWorker


def test_worker_constructs_detector_at_run_start_before_reading_frames():
    calls = []
    detector = SimpleNamespace(detect=lambda frame: ([], 0.0))
    worker = CVWorker(
        camera_id="cam",
        publisher=SimpleNamespace(publish=lambda candidate: None),
        tracker=SimpleNamespace(track=lambda detections, frame: []),
        detector_factory=lambda: calls.append("factory") or detector,
    )
    assert calls == []
    worker.source = SimpleNamespace(
        read_frames=lambda: calls.append("read") or iter([]),
        release=lambda: calls.append("release"),
    )
    worker.adapters = (SimpleNamespace(finalize=lambda: calls.append("finalize")),)

    assert worker.run() == []
    assert worker.detector is detector
    assert calls == ["factory", "read", "finalize", "release"]


def test_worker_detector_factory_failure_prevents_source_read():
    calls = []
    worker = CVWorker(
        camera_id="cam",
        publisher=SimpleNamespace(publish=lambda candidate: None),
        tracker=SimpleNamespace(track=lambda detections, frame: []),
        detector_factory=lambda: (_ for _ in ()).throw(FileNotFoundError("weights missing")),
    )
    worker.source = SimpleNamespace(
        read_frames=lambda: calls.append("read") or iter([]),
        release=lambda: calls.append("release"),
    )
    worker.adapters = (SimpleNamespace(finalize=lambda: calls.append("finalize")),)

    try:
        worker.run()
    except FileNotFoundError as exc:
        assert str(exc) == "weights missing"
    else:
        raise AssertionError("missing detector assets must fail the run")
    assert calls == ["finalize", "release"]


def test_worker_preserves_detector_tracker_store_adapter_manager_publisher_flow():
    frame = FrameData(camera_id="cam", frame_id=1, captured_at="2026-01-01T00:00:00Z",
                      source_type="SIMULATED", source_fps=25, inference_fps=5)
    calls = []
    worker = CVWorker.__new__(CVWorker)
    worker.source = SimpleNamespace(read_frames=lambda: iter([frame]), release=lambda: calls.append("release"))
    worker.health_monitor = SimpleNamespace(update_frame_time=lambda value: None)
    worker.frame_sampler = SimpleNamespace(should_process=lambda value: True)
    worker.detector = SimpleNamespace(detect=lambda value: (calls.append("detect") or ["detection"], 1.0))
    worker.tracker = SimpleNamespace(track=lambda detections, value: (calls.append(tuple(detections)) or ["track"]))
    worker.track_store = SimpleNamespace(update_track=lambda track: calls.append(track) or "state")
    signal = SimpleNamespace(name="signal")
    event = SimpleNamespace(event_id="event")
    worker.adapters = [SimpleNamespace(evaluate=lambda tracks, value: [signal],
                                       finalize=lambda: calls.append("finalize"))]
    worker.event_manager = SimpleNamespace(process=lambda value: event)
    worker.event_id_namespace = lambda value: value
    worker._namespace_event = lambda value: value
    worker.publisher = SimpleNamespace(publish=lambda value: calls.append(value.event_id))
    monkeypatch_validate = __import__("app.cv.worker", fromlist=["validate_event"])
    original_validate = monkeypatch_validate.validate_event
    monkeypatch_validate.validate_event = lambda value: None

    try:
        assert worker.run(max_frames=1) == [event]
    finally:
        monkeypatch_validate.validate_event = original_validate
    assert calls == ["detect", ("detection",), "track", "event", "finalize", "release"]
