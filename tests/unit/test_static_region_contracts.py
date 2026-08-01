import pytest

from app.common.schemas import StaticRegionObservation, VLMValidationResult


def test_static_region_contract_is_serializable_and_immutable():
    region = StaticRegionObservation(region_id="r1", bbox=[1, 2, 3, 4], first_seen_at="2026-08-01T00:00:00Z", last_seen_at="2026-08-01T00:00:02Z", persistence_seconds=2, confidence=.9)
    assert region.model_dump()["region_id"] == "r1"
    with pytest.raises(Exception):
        region.confidence = .2


def test_vlm_verdict_rejects_unknown_values():
    assert VLMValidationResult(verdict="unavailable").verdict == "unavailable"
    with pytest.raises(ValueError):
        VLMValidationResult(verdict="maybe")
