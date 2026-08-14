import numpy as np

from app.common.schemas import StaticRegionObservation
from app.cv.worker import CVWorker
from app.vlm.region_validator import HuggingFaceRegionValidator, TemporalFrame


class DetectorStub:
    def detect(self, frame_data):
        return [], 0.0


def test_real_production_config_constructs_temporal_huggingface_validator_without_network(monkeypatch):
    network_calls = []

    class NoNetworkClient:
        def __init__(self, *args, **kwargs):
            network_calls.append((args, kwargs))
            raise AssertionError("worker construction and missing-token validation must not access network")

    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.setattr("app.vlm.region_validator.httpx.Client", NoNetworkClient)

    worker = CVWorker(camera_id="cam_01", detector=DetectorStub())
    engine = worker.abandoned_engine
    validator = engine.region_validator

    assert engine.temporal_enabled is True
    assert isinstance(validator, HuggingFaceRegionValidator)
    assert validator.model == "google/gemma-3-4b-it"

    region = StaticRegionObservation(
        region_id="region-1",
        bbox=[0, 0, 2, 2],
        first_seen_at="2026-08-01T00:00:00Z",
        last_seen_at="2026-08-01T00:00:00Z",
        persistence_seconds=0,
        confidence=0.9,
    )
    frames = [TemporalFrame(region.first_seen_at, np.zeros((2, 2, 3), dtype=np.uint8))]
    result = validator.validate_temporal(frames, region, region.first_seen_at)

    assert result.verdict == "unavailable"
    assert result.reason == "huggingface_unavailable:missing_token"
    assert network_calls == []
