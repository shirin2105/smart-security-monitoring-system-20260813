"""LLM adapter for event enrichment.

OpenAI-compatible chat completions via langchain-openai `ChatOpenAI`.
No tools are bound (FR-AI-04: the agent never calls tools or performs
external actions). All requests use metadata-only event descriptions;
raw or blurred media is never sent to the provider (PRD §12.1).
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agents.provider import ProviderDraft, ProviderResult
from app.config import settings


def _strip_json_fence(raw: str) -> str:
    text = raw.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    text = "\n".join(lines[1:-1]).strip()
    if text.lower().startswith("json"):
        text = text[4:].strip()
    return text


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

    async def assess(self, *, prompt: str, system_prompt: str) -> ProviderResult:
        return await asyncio.to_thread(self._assess, prompt, system_prompt)

    def _assess(self, prompt: str, system_prompt: str) -> ProviderResult:
        started = time.perf_counter()
        if not self.available:
            return ProviderResult(
                draft=None,
                latency_ms=0.0,
                model_name=self.model,
                error="adapter_unavailable",
            )
        try:
            response = self._llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=prompt)])
            elapsed = round((time.perf_counter() - started) * 1000.0, 2)
            raw = response.content
            if not isinstance(raw, str) or not raw.strip():
                return ProviderResult(
                    draft=None,
                    latency_ms=elapsed,
                    model_name=self.model,
                    error="empty_response",
                )
            return ProviderResult(
                draft=self._parse_draft(raw),
                latency_ms=elapsed,
                model_name=self.model,
                error=None,
            )
        except Exception as exc:
            elapsed = round((time.perf_counter() - started) * 1000.0, 2)
            return ProviderResult(
                draft=None,
                latency_ms=elapsed,
                model_name=self.model,
                error=type(exc).__name__,
            )

    def _parse_draft(self, raw: str) -> ProviderDraft:
        text = _strip_json_fence(raw)
        parsed = json.loads(text)
        return ProviderDraft.model_validate(parsed)


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
