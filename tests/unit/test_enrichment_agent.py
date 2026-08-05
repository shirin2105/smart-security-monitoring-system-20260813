"""Enrichment graph tests: happy path, fallback path, no state mutation."""

import json

import pytest

from app.agents.fallback import build_fallback_output
from app.agents.graph import build_enrichment_graph
from app.common.schemas import EnrichmentOutput, EventCandidate
from tests.unit.test_llm_adapter import _make_adapter

INTRUSION_EVENT = {
    "candidateId": "cam_01-ZONE_INTRUSION-restricted_gate-1",
    "eventType": "ZONE_INTRUSION",
    "cameraId": "cam_01",
    "zoneId": "restricted_gate",
    "sourceType": "SIMULATED",
    "confidence": 0.88,
    "trackCount": 1,
    "observations": {"personCount": 1, "dwellSeconds": 2.5, "insideZone": True},
    "detectedAt": "2026-07-29T10:15:30Z",
    "firstSeenAt": "2026-07-29T10:15:25Z",
    "lastSeenAt": "2026-07-29T10:15:30Z",
    "modelVersion": "yolo-v11n",
    "ruleVersion": "intrusion-rule-v1",
    "policyVersion": 1,
    "artifact": {"available": True, "redactionStatus": "COMPLETE"},
}


def _valid_response():
    return json.dumps({
        "recommendedSeverity": "HIGH",
        "rationale": "Person inside restricted zone beyond dwell",
        "summary": "Intrusion candidate at restricted_gate",
        "actionChecklist": ["Verify zone", "Check authorized personnel"],
    })


@pytest.mark.asyncio
async def test_happy_path_returns_valid_output():
    adapter = _make_adapter(responses=[_valid_response()])
    graph = build_enrichment_graph(llm=adapter)
    result = await graph.ainvoke({"event": INTRUSION_EVENT})

    assert isinstance(result["output"], EnrichmentOutput)
    assert result["output"].recommendedSeverity == "HIGH"
    assert result["fallback_used"] is False
    assert "latency_ms" in result["telemetry"]


@pytest.mark.asyncio
async def test_llm_failure_routes_to_fallback():
    adapter = _make_adapter(responses=["invalid"])
    graph = build_enrichment_graph(llm=adapter)
    result = await graph.ainvoke({"event": INTRUSION_EVENT})

    assert isinstance(result["output"], EnrichmentOutput)
    assert result["fallback_used"] is True
    assert result["output"].rationale.startswith("Fallback")
    assert result["error"] is not None


@pytest.mark.asyncio
async def test_no_adapter_uses_fallback():
    graph = build_enrichment_graph(llm=None)
    result = await graph.ainvoke({"event": INTRUSION_EVENT})

    assert isinstance(result["output"], EnrichmentOutput)
    assert result["fallback_used"] is True


@pytest.mark.asyncio
async def test_graph_never_mutates_input_event():
    import copy

    event_copy = copy.deepcopy(INTRUSION_EVENT)
    adapter = _make_adapter(responses=[_valid_response()])
    graph = build_enrichment_graph(llm=adapter)
    await graph.ainvoke({"event": INTRUSION_EVENT})

    assert INTRUSION_EVENT == event_copy


def test_fallback_respects_event_type_caps():
    abandoned = dict(INTRUSION_EVENT, eventType="ABANDONED_OBJECT")
    output = build_fallback_output(abandoned)
    assert output.recommendedSeverity in {"INFO", "WARNING", "HIGH"}
    assert "CRITICAL" != output.recommendedSeverity


def test_fallback_checklist_from_allow_list():
    output = build_fallback_output(INTRUSION_EVENT)
    assert all(isinstance(item, str) and item.strip() for item in output.actionChecklist)
    assert len(output.actionChecklist) <= 5


def test_event_candidate_serialization_roundtrip():
    """Controlled metadata used by the agent must survive model_dump."""
    candidate = EventCandidate(
        candidateId=INTRUSION_EVENT["candidateId"],
        eventType="ZONE_INTRUSION",
        cameraId="cam_01",
        zoneId="restricted_gate",
        sourceType="SIMULATED",
        detectedAt=INTRUSION_EVENT["detectedAt"],
        firstSeenAt=INTRUSION_EVENT["firstSeenAt"],
        lastSeenAt=INTRUSION_EVENT["lastSeenAt"],
        confidence=0.88,
        trackCount=1,
        observations={"personCount": 1, "dwellSeconds": 2.5, "insideZone": True},
    )
    dumped = candidate.model_dump(mode="json")
    assert dumped["eventType"] == "ZONE_INTRUSION"
    assert dumped["observations"]["personCount"] == 1
    assert "image" not in dumped
