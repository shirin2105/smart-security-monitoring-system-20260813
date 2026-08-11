"""Static-region validation adapters with explicit semantic/offline behavior."""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any, Protocol

import cv2
import httpx
import numpy as np

from app.common.schemas import StaticRegionObservation, VLMValidationResult


@dataclass(frozen=True)
class TemporalFrame:
    captured_at: str
    image: np.ndarray
    source_width: int | None = None
    source_height: int | None = None


class RegionValidator(Protocol):
    def validate(self, crop: np.ndarray, region: StaticRegionObservation) -> VLMValidationResult: ...

    def validate_temporal(self, frames: list[TemporalFrame], region: StaticRegionObservation,
                          event_time: str) -> VLMValidationResult: ...


def validate_temporal_compat(validator: Any, frames: list[TemporalFrame],
                             region: StaticRegionObservation, event_time: str) -> VLMValidationResult:
    method = getattr(validator, "validate_temporal", None)
    if callable(method):
        return method(frames, region, event_time)
    if not frames:
        return VLMValidationResult(verdict="unavailable", reason="temporal:no_frames")
    nearest = min(frames, key=lambda frame: abs(_iso_seconds(frame.captured_at) - _iso_seconds(event_time)))
    return validator.validate(nearest.image, region)


def _iso_seconds(value: str) -> float:
    from datetime import datetime
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


class DisabledRegionValidator:
    def validate(self, crop: np.ndarray, region: StaticRegionObservation) -> VLMValidationResult:
        return VLMValidationResult(verdict="accepted", confidence=region.confidence, reason="validation_disabled")

    def validate_temporal(self, frames, region, event_time):
        return validate_temporal_compat(_SingleImageBridge(self), frames, region, event_time)


class HeuristicRegionValidator:
    """Deterministic crop-quality heuristic; this is not semantic VLM inference."""

    def __init__(self, min_pixels: int = 64, min_stddev: float = 2.0):
        self.min_pixels = min_pixels
        self.min_stddev = min_stddev

    def validate(self, crop: np.ndarray, region: StaticRegionObservation) -> VLMValidationResult:
        if not isinstance(crop, np.ndarray) or crop.size < self.min_pixels or crop.ndim not in (2, 3):
            return VLMValidationResult(verdict="rejected", reason="heuristic:invalid_or_empty_crop")
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
        contrast = float(np.std(gray))
        if contrast < self.min_stddev:
            return VLMValidationResult(verdict="rejected", reason="heuristic:insufficient_visual_detail")
        confidence = min(float(region.confidence), min(0.99, contrast / 64.0))
        return VLMValidationResult(verdict="accepted", confidence=round(confidence, 4), reason="heuristic:visual_detail")

    def validate_temporal(self, frames, region, event_time):
        return validate_temporal_compat(_SingleImageBridge(self), frames, region, event_time)


class _SingleImageBridge:
    def __init__(self, validator: Any):
        self.validator = validator

    def validate(self, image, region):
        return self.validator.validate(image, region)


# Compatibility name; CLI/config call the mode "heuristic" so it cannot be mistaken for a VLM.
LocalRegionValidator = HeuristicRegionValidator


class HuggingFaceRegionValidator:
    """Call the HF OpenAI-compatible multimodal chat endpoint and parse strict JSON."""

    PROMPT = (
        "Inspect this crop from a fixed security camera. Is there a newly placed unattended "
        "physical object (such as a bag, parcel, or luggage) in the crop? Return only JSON "
        'with exactly: {"verdict":"accepted|rejected","confidence":0.0,"reason":"brief"}.'
    )
    TEMPORAL_PROMPT = (
        "Inspect these full security-camera scene frames in chronological order around the candidate event time. "
        "Determine whether the sequence shows a physical object being left behind and remaining unattended. "
        "Use temporal changes across all frames, not a single-frame guess. Return only JSON with exactly: "
        '{"verdict":"accepted|rejected","confidence":0.0,"reason":"brief"}.'
    )

    def __init__(self, model: str = "google/gemma-3-4b-it", token: str | None = None,
                 timeout_seconds: float = 8.0, max_dimension: int = 768,
                 max_jpeg_bytes: int = 750_000, max_request_bytes: int = 12_000_000,
                 client: Any | None = None):
        self.model = model
        self.token = token if token is not None else os.getenv("HF_TOKEN")
        self.timeout_seconds = max(0.1, min(float(timeout_seconds), 30.0))
        self.max_dimension = max(64, min(int(max_dimension), 1536))
        self.max_jpeg_bytes = max(16_384, min(int(max_jpeg_bytes), 2_000_000))
        self.max_request_bytes = max(64_000, min(int(max_request_bytes), 25_000_000))
        self.client = client

    @staticmethod
    def _unavailable(cause: str) -> VLMValidationResult:
        return VLMValidationResult(verdict="unavailable", reason=f"huggingface_unavailable:{cause}")

    @staticmethod
    def _parse(payload: Any) -> VLMValidationResult:
        content = payload["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("message content must be text")
        text = content.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1]).strip()
            if text.lower().startswith("json"):
                text = text[4:].strip()
        parsed = json.loads(text)
        if not isinstance(parsed, dict) or set(parsed) != {"verdict", "confidence", "reason"}:
            raise ValueError("response must contain exactly verdict, confidence, reason")
        if parsed["verdict"] not in {"accepted", "rejected"}:
            raise ValueError("invalid verdict")
        confidence = parsed["confidence"]
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise ValueError("invalid confidence")
        if not isinstance(parsed["reason"], str) or not parsed["reason"].strip():
            raise ValueError("invalid reason")
        return VLMValidationResult(verdict=parsed["verdict"], confidence=round(float(confidence), 4),
                                   reason=f"huggingface_vlm:{parsed['reason'].strip()}")

    def _encode(self, crop: np.ndarray) -> bytes:
        return self._encode_at(crop, self.max_dimension, 82)

    def _encode_at(self, crop: np.ndarray, max_dimension: int, quality: int) -> bytes:
        if not isinstance(crop, np.ndarray) or crop.size == 0 or crop.ndim not in (2, 3):
            raise ValueError("invalid_crop")
        height, width = crop.shape[:2]
        scale = min(1.0, max_dimension / max(height, width))
        if scale < 1.0:
            crop = cv2.resize(crop, (max(1, round(width * scale)), max(1, round(height * scale))))
        ok, encoded = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if not ok or len(encoded) > self.max_jpeg_bytes:
            raise ValueError("crop_encode_or_size")
        return encoded.tobytes()

    def validate(self, crop: np.ndarray, region: StaticRegionObservation) -> VLMValidationResult:
        if not self.token:
            return self._unavailable("missing_token")
        try:
            encoded = self._encode(crop)
            data_uri = "data:image/jpeg;base64," + base64.b64encode(encoded).decode("ascii")
            payload = {"model": self.model, "temperature": 0, "max_tokens": 120,
                       "response_format": {"type": "json_object"}, "messages": [{"role": "user", "content": [
                           {"type": "text", "text": self.PROMPT},
                           {"type": "image_url", "image_url": {"url": data_uri}},
                       ]}]}
            headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
            url = "https://router.huggingface.co/v1/chat/completions"
            if self.client is None:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(url, headers=headers, json=payload)
            else:
                response = self.client.post(url, headers=headers, json=payload, timeout=self.timeout_seconds)
            response.raise_for_status()
            return self._parse(response.json())
        except (httpx.HTTPError, ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError) as exc:
            return self._unavailable(type(exc).__name__)

    def validate_temporal(self, frames: list[TemporalFrame], region: StaticRegionObservation,
                          event_time: str) -> VLMValidationResult:
        if not self.token:
            return self._unavailable("missing_token")
        try:
            if not 1 <= len(frames) <= 17:
                raise ValueError("temporal_frame_count")
            timestamps = [_iso_seconds(frame.captured_at) for frame in frames]
            if timestamps != sorted(timestamps) or len(set(timestamps)) != len(timestamps):
                raise ValueError("temporal_frame_order")
            payload = self._build_temporal_payload(frames, region, event_time)
            if payload is None:
                return self._unavailable("request_too_large")
            headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
            url = "https://router.huggingface.co/v1/chat/completions"
            if self.client is None:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(url, headers=headers, json=payload)
            else:
                response = self.client.post(url, headers=headers, json=payload, timeout=self.timeout_seconds)
            response.raise_for_status()
            return self._parse(response.json())
        except (httpx.HTTPError, ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError) as exc:
            return self._unavailable(type(exc).__name__)

    def _build_temporal_payload(self, frames: list[TemporalFrame], region: StaticRegionObservation,
                                event_time: str) -> dict[str, Any] | None:
        event_seconds = _iso_seconds(event_time)
        for count in [len(frames), 13, 9, 5, 3]:
            count = min(count, len(frames))
            if count < 1:
                continue
            if count == len(frames):
                selected = frames
            else:
                indices = {round(index * (len(frames) - 1) / (count - 1)) for index in range(count)}
                nearest = min(range(len(frames)), key=lambda index: abs(
                    _iso_seconds(frames[index].captured_at) - event_seconds))
                indices.add(nearest)
                selected = [frames[index] for index in sorted(indices)]
            for dimension, quality in ((self.max_dimension, 82),
                                       (max(160, int(self.max_dimension * .8)), 65),
                                       (max(160, int(self.max_dimension * .6)), 50)):
                content = [{"type": "text", "text": self.TEMPORAL_PROMPT}]
                try:
                    for frame in selected:
                        height, width = frame.image.shape[:2]
                        source_width = frame.source_width or width
                        source_height = frame.source_height or height
                        x1, y1, x2, y2 = region.bbox
                        normalized = [round(x1 / source_width, 4), round(y1 / source_height, 4),
                                      round(x2 / source_width, 4), round(y2 / source_height, 4)]
                        pixels = [round(normalized[0] * width), round(normalized[1] * height),
                                  round(normalized[2] * width), round(normalized[3] * height)]
                        offset = _iso_seconds(frame.captured_at) - event_seconds
                        content.append({"type": "text", "text":
                            f"Frame offset {offset:+.3f}s from T; candidate bbox pixels "
                            f"{pixels}; normalized bbox {normalized}."})
                        encoded = self._encode_at(frame.image, dimension, quality)
                        uri = "data:image/jpeg;base64," + base64.b64encode(encoded).decode("ascii")
                        content.append({"type": "image_url", "image_url": {"url": uri}})
                except ValueError:
                    continue
                payload = {"model": self.model, "temperature": 0, "max_tokens": 120,
                           "response_format": {"type": "json_object"},
                           "messages": [{"role": "user", "content": content}]}
                if len(json.dumps(payload, separators=(",", ":")).encode("utf-8")) <= self.max_request_bytes:
                    return payload
        return None


def create_region_validator(mode: str, *, model: str = "google/gemma-3-4b-it",
                            timeout_seconds: float = 8.0) -> RegionValidator:
    normalized = mode.strip().lower()
    if normalized == "disabled":
        return DisabledRegionValidator()
    if normalized in {"heuristic", "local"}:
        return HeuristicRegionValidator()
    if normalized == "huggingface":
        return HuggingFaceRegionValidator(model=model, timeout_seconds=timeout_seconds)
    raise ValueError(f"unsupported VLM mode: {mode}")
