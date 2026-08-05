"""LLM adapter for event enrichment.

OpenAI-compatible chat completions via langchain-openai `ChatOpenAI`.
No tools are bound (FR-AI-04: the agent never calls tools or performs
external actions). All requests use metadata-only event descriptions;
raw or blurred media is never sent to the provider (PRD §12.1).
"""

from __future__ import annotations

import json
import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from app.common.schemas import EnrichmentOutput
from app.config import settings


class LLMAdapter:
    """Wrapper around an OpenAI-compatible chat model with strict schema validation."""

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str,
        timeout_seconds: float = 15.0,
        temperature: float = 0.0,
        client: Any | None = None,
        llm: Any | None = None,
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.timeout_seconds = max(0.1, min(float(timeout_seconds), 30.0))
        self.temperature = temperature
        self._client = client
        if llm is not None:
            self._llm = llm
        elif api_key:
            self._llm = ChatOpenAI(
                model=model,
                api_key=api_key,
                base_url=base_url,
                temperature=temperature,
                timeout=self.timeout_seconds,
                max_retries=0,
                http_client=self._client,
            )
        else:
            # No credential configured: adapter reports unavailable instead of
            # constructing a client that would raise at call time.
            self._llm = None

    @property
    def available(self) -> bool:
        return self._llm is not None

    def enrich(
        self,
        prompt: str,
        system_prompt: str,
    ) -> tuple[EnrichmentOutput | None, dict[str, Any] | None]:
        """Call the model and validate the structured JSON output.

        Returns ``(output, telemetry)``. On provider failure, timeout, or
        schema-invalid response, ``output`` is ``None`` and the caller must
        apply its deterministic fallback (FR-AI-06).
        """
        started = time.perf_counter()
        if not self.available:
            elapsed = (time.perf_counter() - started) * 1000.0
            return None, self._telemetry(elapsed, "adapter_unavailable")

        try:
            response = self._llm.invoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]
            )
            raw = response.content
            elapsed = (time.perf_counter() - started) * 1000.0
            if not isinstance(raw, str) or not raw.strip():
                return None, self._telemetry(elapsed, "empty_response")
            output = self._parse_output(raw)
            return output, self._telemetry(elapsed, None, output is not None)
        except Exception as exc:  # provider/network/schema failures never block the pipeline
            elapsed = (time.perf_counter() - started) * 1000.0
            return None, self._telemetry(elapsed, type(exc).__name__)

    def _parse_output(self, raw: str) -> EnrichmentOutput | None:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1]).strip()
            if text.lower().startswith("json"):
                text = text[4:].strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None
        try:
            return EnrichmentOutput.model_validate(parsed)
        except ValidationError:
            return None

    def _telemetry(
        self,
        latency_ms: float,
        error: str | None,
        output_valid: bool | None = None,
    ) -> dict[str, Any]:
        return {
            "latency_ms": round(latency_ms, 2),
            "model": self.model,
            "error": error,
            "output_valid": output_valid,
        }


def create_llm_adapter(
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    timeout_seconds: float | None = None,
    client: Any | None = None,
) -> LLMAdapter:
    """Build an adapter from settings with optional overrides (tests inject clients)."""
    return LLMAdapter(
        model=model or settings.llm_model,
        api_key=api_key if api_key is not None else settings.llm_api_key,
        base_url=base_url or settings.llm_base_url,
        timeout_seconds=timeout_seconds if timeout_seconds is not None else settings.llm_timeout_seconds,
        temperature=settings.llm_temperature,
        client=client,
    )
