from types import SimpleNamespace
from unittest.mock import Mock

from app.cv.worker import CVWorker
from app.cv.event_manager import CVEventManager
from app.cv.events.event_signal import EventSignal


def test_worker_defaults_to_cv_event_jsonl_publisher(monkeypatch, tmp_path):
    publisher_factory = Mock(return_value=Mock())
    monkeypatch.setattr("app.cv.worker.JsonlPublisher", publisher_factory)
    monkeypatch.setattr("app.cv.worker.settings.artifact_dir", tmp_path)

    worker = CVWorker(
        camera_id="cam_test",
        source_uri="clip.mp4",
        detector=Mock(),
        tracker=SimpleNamespace(track=lambda detections, frame: []),
    )

    publisher_factory.assert_called_once_with(
        output_path=tmp_path / "events" / "cv-events.jsonl"
    )
    assert worker.publisher is publisher_factory.return_value


def test_invalid_phase7c_config_fails_during_construction(monkeypatch):
    rules = {"abandoned_object": {"phase7c": {"owner": {"min_association_score": 1.1}}}}
    monkeypatch.setattr(type(__import__("app.cv.worker", fromlist=["settings"]).settings),
                        "event_rules", property(lambda self: rules))

    try:
        CVWorker(
            camera_id="cam_test",
            detector=Mock(),
            tracker=SimpleNamespace(track=lambda detections, frame: []),
        )
    except ValueError as error:
        assert "min_association_score" in str(error)
    else:
        raise AssertionError("invalid Phase7C config must fail before frame processing")


def test_invalid_phase7c_debug_config_fails_during_construction(monkeypatch):
    rules = {"abandoned_object": {"phase7c": {"debug": {"enabled": "yes"}}}}
    monkeypatch.setattr(type(__import__("app.cv.worker", fromlist=["settings"]).settings),
                        "event_rules", property(lambda self: rules))

    try:
        CVWorker(
            camera_id="cam_test",
            detector=Mock(),
            tracker=SimpleNamespace(track=lambda detections, frame: []),
        )
    except ValueError as error:
        assert "debug.enabled" in str(error)
    else:
        raise AssertionError("invalid Phase7C debug config must fail before frame processing")


def test_namespaced_failed_start_is_rolled_back_without_orphan_end():
    manager = CVEventManager("cam_test", run_id="run")
    signal = EventSignal(
        "cam_test", "ZONE_INTRUSION", "zone:7", True,
        "2026-01-01T00:00:01Z", 1.0, 0.9,
        {"persons": [{"track_id": 7, "bbox_xyxy": [0, 0, 10, 10]}]},
        {"zone_id": "zone", "inside_duration_s": 1.0},
    )
    original = manager.process(signal)
    worker = object.__new__(CVWorker)
    worker.event_manager = manager
    worker.publisher = SimpleNamespace(publish=lambda _event: False)
    namespaced = type(original).from_dict({
        **original.to_dict(), "event_id": f"prefix-{original.event_id}"
    })

    try:
        worker._publish(namespaced, original.event_id)
    except RuntimeError:
        pass
    else:
        raise AssertionError("failed publish must raise")

    assert manager.end_all() == []
