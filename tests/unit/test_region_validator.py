import numpy as np
import pytest

from app.common.schemas import StaticRegionObservation
from app.vlm.region_validator import (
    HuggingFaceRegionValidator,
    LocalRegionValidator,
    TemporalFrame,
    validate_temporal_compat,
    create_region_validator,
)


@pytest.fixture
def region():
    return StaticRegionObservation(
        region_id="r1", bbox=[0, 0, 16, 16], first_seen_at="2026-08-01T00:00:00Z",
        last_seen_at="2026-08-01T00:00:02Z", persistence_seconds=2, confidence=0.8,
    )


def detailed_crop():
    crop = np.zeros((16, 16, 3), dtype=np.uint8)
    crop[:, 8:] = 200
    return crop


def test_disabled_preserves_cv_verdict(region):
    result = create_region_validator("disabled").validate(np.empty((0, 0, 3)), region)
    assert result.verdict == "accepted"
    assert result.reason == "validation_disabled"


def test_local_is_deterministic_and_rejects_blank_crop(region):
    validator = LocalRegionValidator()
    first = validator.validate(detailed_crop(), region)
    assert first == validator.validate(detailed_crop(), region)
    assert first.verdict == "accepted"
    assert validator.validate(np.zeros((16, 16, 3), dtype=np.uint8), region).verdict == "rejected"


def test_huggingface_missing_token_is_unavailable_without_network(region):
    class NoNetwork:
        def post(self, *args, **kwargs):
            raise AssertionError("network must not be called")

    validator = HuggingFaceRegionValidator("model", token=None, client=NoNetwork())
    validator.token = None
    result = validator.validate(detailed_crop(), region)
    assert result.verdict == "unavailable"
    assert result.reason == "huggingface_unavailable:missing_token"


@pytest.mark.parametrize("payload", [{}, [], {"choices": []}, {"choices": [{"message": {"content": "not-json"}}]}])
def test_huggingface_malformed_payload_is_unavailable(region, payload):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return payload

    class Client:
        def post(self, *args, **kwargs):
            return Response()

    result = HuggingFaceRegionValidator("model", token="test", client=Client()).validate(detailed_crop(), region)
    assert result.verdict == "unavailable"
    assert result.reason.startswith("huggingface_unavailable:")


def test_huggingface_strict_valid_result(region):
    result = HuggingFaceRegionValidator._parse({"choices": [{"message": {"content":
        '{"verdict":"accepted","confidence":0.91,"reason":"suitcase visible"}'}}]})
    assert result.verdict == "accepted"
    assert result.confidence == 0.91


def test_huggingface_sends_multimodal_chat_request(region):
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {"choices": [{"message": {"content":
                '{"verdict":"rejected","confidence":0.8,"reason":"person only"}'}}]}
    class Client:
        def post(self, url, **kwargs):
            assert url.endswith("/v1/chat/completions")
            content = kwargs["json"]["messages"][0]["content"]
            assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
            return Response()
    result = HuggingFaceRegionValidator(token="test", client=Client()).validate(detailed_crop(), region)
    assert result.verdict == "rejected"
    assert result.reason == "huggingface_vlm:person only"


def test_unknown_mode_is_rejected():
    with pytest.raises(ValueError, match="unsupported VLM mode"):
        create_region_validator("cloud")


def test_huggingface_temporal_sends_ordered_full_frames(region):
    captured = {}
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {"choices": [{"message": {"content":
                '{"verdict":"accepted","confidence":0.9,"reason":"object left"}'}}]}
    class Client:
        def post(self, url, **kwargs):
            captured.update(kwargs["json"])
            return Response()
    frames = [TemporalFrame(f"2026-08-01T00:00:{second:02d}Z",
                            np.full((20, 30, 3), second, dtype=np.uint8)) for second in range(17)]
    result = HuggingFaceRegionValidator(token="test", client=Client()).validate_temporal(
        frames, region, "2026-08-01T00:00:08Z")
    content = captured["messages"][0]["content"]
    assert result.verdict == "accepted"
    assert "chronological order" in content[0]["text"]
    assert len([part for part in content if part["type"] == "image_url"]) == 17


def test_temporal_validation_rejects_bad_count_and_order_without_network(region):
    class NoNetwork:
        def post(self, *args, **kwargs): raise AssertionError("must not call")
    validator = HuggingFaceRegionValidator(token="test", client=NoNetwork())
    image = detailed_crop()
    assert validator.validate_temporal([], region, region.first_seen_at).verdict == "unavailable"
    unordered = [TemporalFrame("2026-08-01T00:00:02Z", image),
                 TemporalFrame("2026-08-01T00:00:01Z", image)]
    assert validator.validate_temporal(unordered, region, region.first_seen_at).verdict == "unavailable"


def test_old_validator_temporal_bridge_uses_event_nearest_frame(region):
    class OldValidator:
        def validate(self, image, region):
            return VLMValidationResult(verdict="accepted", confidence=float(image[0, 0, 0]) / 10,
                                       reason="old")
    from app.common.schemas import VLMValidationResult
    frames = [TemporalFrame("2026-08-01T00:00:00Z", np.zeros((2, 2, 3), dtype=np.uint8)),
              TemporalFrame("2026-08-01T00:00:02Z", np.full((2, 2, 3), 5, dtype=np.uint8))]
    assert validate_temporal_compat(OldValidator(), frames, region,
                                    "2026-08-01T00:00:02Z").confidence == .5


def test_temporal_payload_labels_offsets_bbox_and_stays_under_aggregate_cap(region):
    captured = {}
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {"choices": [{"message": {"content":
                '{"verdict":"accepted","confidence":0.8,"reason":"left behind"}'}}]}
    class Client:
        def post(self, url, **kwargs):
            captured["payload"] = kwargs["json"]
            return Response()
    rng = np.random.default_rng(4)
    frames = [TemporalFrame(f"2026-08-01T00:00:{second:02d}Z",
        rng.integers(0, 256, (480, 640, 3), dtype=np.uint8), 1920, 1080) for second in range(17)]
    validator = HuggingFaceRegionValidator(token="test", client=Client(), max_request_bytes=500_000)
    result = validator.validate_temporal(frames, region, "2026-08-01T00:00:08Z")
    assert result.verdict == "accepted"
    encoded_size = len(__import__("json").dumps(captured["payload"], separators=(",", ":")).encode())
    assert encoded_size <= 500_000
    labels = [part["text"] for part in captured["payload"]["messages"][0]["content"][1::2]]
    assert labels[0].startswith("Frame offset -8.000s")
    assert labels[-1].startswith("Frame offset +8.000s")
    assert all("normalized bbox" in label and "candidate bbox pixels" in label for label in labels)


def test_temporal_request_too_large_does_not_call_network(region):
    class NoNetwork:
        def post(self, *args, **kwargs): raise AssertionError("must not call")
    noisy = np.random.default_rng(5).integers(0, 256, (480, 640, 3), dtype=np.uint8)
    frames = [TemporalFrame(f"2026-08-01T00:00:{second:02d}Z", noisy) for second in range(17)]
    validator = HuggingFaceRegionValidator(token="test", client=NoNetwork(), max_request_bytes=64_000)
    result = validator.validate_temporal(frames, region, "2026-08-01T00:00:08Z")
    assert result.verdict == "unavailable"
    assert result.reason == "huggingface_unavailable:request_too_large"
