from unittest.mock import Mock

from app.cv.worker import CVWorker


def test_worker_propagates_event_ingest_settings(monkeypatch):
    publisher_factory = Mock(return_value=Mock())
    monkeypatch.setattr("app.cv.worker.HttpEventPublisher", publisher_factory)
    monkeypatch.setattr("app.cv.worker.settings.event_ingest_url", "http://backend/ingest")
    monkeypatch.setattr("app.cv.worker.settings.event_ingest_token", "producer-secret")
    monkeypatch.setattr("app.cv.worker.settings.event_ingest_timeout_seconds", 2.5)
    monkeypatch.setattr("app.cv.worker.settings.event_ingest_max_attempts", 4)
    worker = CVWorker(camera_id="cam_test", source_uri="clip.mp4", detector=Mock())

    publisher_factory.assert_called_once_with(
        endpoint_url="http://backend/ingest",
        bearer_token="producer-secret",
        timeout_seconds=2.5,
        max_retries=4,
    )
    assert worker.publisher is publisher_factory.return_value
