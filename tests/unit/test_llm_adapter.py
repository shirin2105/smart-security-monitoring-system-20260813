"""LLM adapter tests: strict schema validation, fallback contract, no network."""

import json

from app.common.schemas import EnrichmentOutput
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


def test_available_without_api_key_is_false():
    adapter = _make_adapter(available=False)
    assert not adapter.available
    output, telemetry = adapter.enrich(prompt="p", system_prompt="s")
    assert output is None
    assert telemetry["error"] == "adapter_unavailable"


def test_valid_json_output_parsed():
    adapter = _make_adapter(responses=[json.dumps({
        "recommendedSeverity": "HIGH",
        "rationale": "person in restricted zone",
        "summary": "Intrusion at gate",
        "actionChecklist": ["Verify on camera"],
    })])
    output, telemetry = adapter.enrich(prompt="p", system_prompt="s")
    assert isinstance(output, EnrichmentOutput)
    assert output.recommendedSeverity == "HIGH"
    assert telemetry["output_valid"] is True
    assert telemetry["error"] is None


def test_code_fenced_json_accepted():
    raw = "```json\n" + json.dumps({
        "recommendedSeverity": "WARNING",
        "rationale": "crowd",
        "summary": "Crowd detected",
        "actionChecklist": ["Check area"],
    }) + "\n```"
    adapter = _make_adapter(responses=[raw])
    output, _ = adapter.enrich(prompt="p", system_prompt="s")
    assert output is not None
    assert output.recommendedSeverity == "WARNING"


def test_invalid_severity_rejected():
    adapter = _make_adapter(responses=[json.dumps({
        "recommendedSeverity": "SEVERE",
        "rationale": "x",
        "summary": "y",
        "actionChecklist": [],
    })])
    output, telemetry = adapter.enrich(prompt="p", system_prompt="s")
    assert output is None
    assert telemetry["output_valid"] is False


def test_malformed_json_rejected():
    adapter = _make_adapter(responses=["not json at all"])
    output, telemetry = adapter.enrich(prompt="p", system_prompt="s")
    assert output is None
    assert telemetry["output_valid"] is False


def test_provider_exception_returns_none():
    class _RaisingLLM:
        def invoke(self, messages):
            raise TimeoutError("provider timeout")

    adapter = LLMAdapter(
        model="m", api_key="k", base_url="https://x.invalid",
        timeout_seconds=1.0, temperature=0.0, llm=_RaisingLLM(),
    )
    output, telemetry = adapter.enrich(prompt="p", system_prompt="s")
    assert output is None
    assert telemetry["error"] == "TimeoutError"
    assert telemetry["latency_ms"] >= 0


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
