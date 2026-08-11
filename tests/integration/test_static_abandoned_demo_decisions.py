import cv2
import numpy as np
import pytest

from app.common.schemas import StaticRegionObservation, VLMValidationResult
from scripts import generate_static_abandoned_demo as demo


def test_hf_rejection_is_successful_semantic_decision_without_alert(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"mp4v"), 1.0, (64, 48))
    assert writer.isOpened()
    for second in range(12):
        writer.write(np.full((48, 64, 3), second * 10, dtype=np.uint8))
    writer.release()

    region = StaticRegionObservation(region_id="r1", bbox=[8, 8, 24, 24],
        first_seen_at=demo.START_ISO, last_seen_at=demo.START_ISO,
        persistence_seconds=6, confidence=.9)
    class Detector:
        def __init__(self, *args): pass
        def update(self, image, timestamp): return [region]
    class Validator:
        def validate_temporal(self, frames, observation, event_time):
            return VLMValidationResult(verdict="rejected", confidence=.95,
                                       reason="huggingface_vlm:not unattended")

    monkeypatch.setattr(demo, "ROOT", tmp_path)
    monkeypatch.setattr(demo, "StaticRegionDetector", Detector)
    monkeypatch.setattr(demo, "create_region_validator", lambda *args, **kwargs: Validator())
    summary = demo.generate(source, tmp_path / "out.mp4", tmp_path / "summary.json",
                            "huggingface", owner_absent_seconds=0, max_vlm_decisions=1)
    assert summary["event_count"] == 0
    assert summary["validation_decision_count"] == 1
    assert summary["semantic_vlm_executed"] is True
    assert summary["validation_decisions"][0]["validation"]["verdict"] == "rejected"
    assert summary["candidate_time"] < summary["decision_time"]
    assert summary["processing_truncated"] is True
    assert "token" not in (tmp_path / "summary.json").read_text(encoding="utf-8").lower()


def test_hf_unavailable_failure_has_sanitized_auditable_diagnostics(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"mp4v"), 1.0, (64, 48))
    assert writer.isOpened()
    for second in range(12):
        writer.write(np.full((48, 64, 3), second, dtype=np.uint8))
    writer.release()
    region = StaticRegionObservation(region_id="r1", bbox=[8, 8, 24, 24],
        first_seen_at=demo.START_ISO, last_seen_at=demo.START_ISO,
        persistence_seconds=6, confidence=.9)
    class Detector:
        def __init__(self, *args): pass
        def update(self, image, timestamp): return [region]
    class Validator:
        def validate_temporal(self, frames, observation, event_time):
            return VLMValidationResult(verdict="unavailable",
                reason="provider timeout Bearer secret-value hf_abcdefghijk")
    monkeypatch.setattr(demo, "ROOT", tmp_path)
    monkeypatch.setattr(demo, "StaticRegionDetector", Detector)
    monkeypatch.setattr(demo, "create_region_validator", lambda *args, **kwargs: Validator())
    summary_path = tmp_path / "failure.json"
    with pytest.raises(RuntimeError) as raised:
        demo.generate(source, tmp_path / "out.mp4", summary_path, "huggingface",
                      owner_absent_seconds=0, max_vlm_decisions=1)
    message = str(raised.value)
    assert "decisions=1" in message and "unavailable" in message
    assert "secret-value" not in message and "hf_abcdefghijk" not in message
    failure = __import__("json").loads(summary_path.read_text(encoding="utf-8"))
    assert failure["validation_decision_count"] == 1
    assert failure["semantic_vlm_executed"] is False
    serialized = summary_path.read_text(encoding="utf-8")
    assert "secret-value" not in serialized and "hf_abcdefghijk" not in serialized
