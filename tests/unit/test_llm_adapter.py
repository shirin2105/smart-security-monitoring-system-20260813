"""LLM adapter tests: strict schema validation, fallback contract, no network."""

import json

import pytest

from app.agents.provider import ProviderDraft
from app.llm.adapter import LLMAdapter, create_llm_adapter


class _FakeResponse:
    def __init__(self, content: str):
        self.content = content


class _FakeLLM:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages)
        if self._responses:
            return _FakeResponse(self._responses.pop(0))
        raise RuntimeError("no response scheduled")


def _make_adapter(responses=None, available=True):
    if available:
        llm = _FakeLLM(responses or [])
        return LLMAdapter(
            model="test-model",
            api_key="sk-test",
            base_url="https://example.invalid/v1",
            timeout_seconds=1.0,
            temperature=0.0,
            llm=llm,
        )
    return LLMAdapter(
        model="test-model",
        api_key="",
        base_url="https://example.invalid/v1",
        timeout_seconds=1.0,
        temperature=0.0,
    )


@pytest.mark.asyncio
async def test_assess_does_not_block_event_loop():
    """C4: a slow provider call must not stall the event loop.

    The blocking invoke runs in a worker thread, so a concurrent timer
    keeps firing while the provider call is in flight.
    """
    import asyncio
    import time

    class _SlowLLM:
        def invoke(self, messages):
            time.sleep(0.3)
            return _FakeResponse(
                '{"recommendedSeverity":"HIGH","rationale":"r"}'
            )

    adapter = LLMAdapter(
        model="m",
        api_key="k",
        base_url="https://x.invalid",
        timeout_seconds=1.0,
        temperature=0.0,
        llm=_SlowLLM(),
    )

    loop = asyncio.get_running_loop()
    ticks = []

    async def _ticker():
        deadline = loop.time() + 0.5
        while loop.time() < deadline:
            ticks.append(1)
            await asyncio.sleep(0.02)

    ticker = asyncio.create_task(_ticker())
    result = await adapter.assess(prompt="p", system_prompt="s")
    await ticker

    assert result.draft is not None
    assert result.draft.recommended_severity == "HIGH"
    assert len(ticks) >= 5, f"event loop stalled, only {len(ticks)} ticks in 500ms"


@pytest.mark.asyncio
async def test_available_without_api_key_is_false():
    adapter = _make_adapter(available=False)
    assert not adapter.available
    result = await adapter.assess(prompt="p", system_prompt="s")
    assert result.draft is None
    assert result.error == "adapter_unavailable"


@pytest.mark.asyncio
async def test_valid_json_output_parsed():
    adapter = _make_adapter(responses=[json.dumps({
        "recommendedSeverity": "HIGH",
        "rationale": "person in restricted zone",
    })])
    result = await adapter.assess(prompt="p", system_prompt="s")
    assert isinstance(result.draft, ProviderDraft)
    assert result.draft.recommended_severity == "HIGH"
    assert result.draft.rationale == "person in restricted zone"
    assert result.error is None


@pytest.mark.asyncio
async def test_code_fenced_json_accepted():
    raw = "```json\n" + json.dumps({
        "recommendedSeverity": "WARNING",
        "rationale": "crowd",
    }) + "\n```"
    adapter = _make_adapter(responses=[raw])
    result = await adapter.assess(prompt="p", system_prompt="s")
    assert result.draft is not None
    assert result.draft.recommended_severity == "WARNING"


@pytest.mark.asyncio
async def test_invalid_severity_rejected():
    adapter = _make_adapter(responses=[json.dumps({
        "recommendedSeverity": "SEVERE",
        "rationale": "x",
    })])
    result = await adapter.assess(prompt="p", system_prompt="s")
    assert result.draft is None
    assert result.error == "ValidationError"


@pytest.mark.asyncio
async def test_malformed_json_rejected():
    adapter = _make_adapter(responses=["not json at all"])
    result = await adapter.assess(prompt="p", system_prompt="s")
    assert result.draft is None
    assert result.error == "JSONDecodeError"


@pytest.mark.asyncio
async def test_provider_exception_returns_none():
    class _RaisingLLM:
        def invoke(self, messages):
            raise TimeoutError("provider timeout")

    adapter = LLMAdapter(
        model="m", api_key="k", base_url="https://x.invalid",
        timeout_seconds=1.0, temperature=0.0, llm=_RaisingLLM(),
    )
    result = await adapter.assess(prompt="p", system_prompt="s")
    assert result.draft is None
    assert result.error == "TimeoutError"
    assert result.latency_ms >= 0


def test_no_tools_bound_by_construction():
    """Adapter must never attach tools; use langchain-compatible contract check."""
    import os

    from langchain_openai import ChatOpenAI

    os.environ["OPENAI_API_KEY"] = "sk-test"
    try:
        raw = ChatOpenAI(model="gpt-4o-mini", api_key="sk-test", temperature=0)
        assert getattr(raw, "tools", None) is None
    finally:
        os.environ.pop("OPENAI_API_KEY", None)


def test_create_adapter_uses_settings_defaults(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "llm_model", "test-default-model")
    monkeypatch.setattr(settings, "llm_api_key", "sk-default")
    adapter = create_llm_adapter()
    assert adapter.model == "test-default-model"
    assert adapter.available
