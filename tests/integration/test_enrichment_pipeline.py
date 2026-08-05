"""Integration: persisted candidate JSON → enrichment graph → valid output or fallback."""

import json

import pytest

from app.agents.graph import build_enrichment_graph
from app.common.schemas import EnrichmentOutput, EventCandidate
from tests.unit.test_enrichment_agent import INTRUSION_EVENT
from tests.unit.test_llm_adapter import _make_adapter

VALID_LLM_RESPONSE = json.dumps({
    "recommendedSeverity": "HIGH",
    "rationale": "Person inside restricted zone beyond dwell",
    "summary": "Intrusion candidate at restricted_gate",
    "actionChecklist": ["Verify zone", "Check authorized personnel"],
})


def test_candidate_dump_roundtrip_matches_backend_ingest(tmp_path):
    """Backend persists EventCandidate as JSON; the agent consumes that JSON."""
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
    # Mirrors app/api/events.py: candidate.model_dump(mode="json") persisted to disk
    persisted = candidate.model_dump(mode="json")
    file_path = tmp_path / "candidate.json"
    file_path.write_text(json.dumps(persisted, ensure_ascii=False), encoding="utf-8")

    loaded = json.loads(file_path.read_text(encoding="utf-8"))
    revalidated = EventCandidate.model_validate(loaded)
    assert revalidated.candidateId == INTRUSION_EVENT["candidateId"]
    assert revalidated.eventType.value == "ZONE_INTRUSION"


@pytest.mark.asyncio
async def test_enrichment_from_persisted_json_with_llm(tmp_path):
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
    persisted = candidate.model_dump(mode="json")

    adapter = _make_adapter(responses=[VALID_LLM_RESPONSE])
    graph = build_enrichment_graph(llm=adapter)
    result = await graph.ainvoke({"event": persisted})

    assert isinstance(result["output"], EnrichmentOutput)
    assert result["output"].recommendedSeverity == "HIGH"
    assert result["fallback_used"] is False


@pytest.mark.asyncio
async def test_enrichment_fallback_when_llm_outage(tmp_path):
    """LLM outage must never block enrichment; deterministic fallback applies."""
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
    persisted = candidate.model_dump(mode="json")

    adapter = _make_adapter(available=False)
    graph = build_enrichment_graph(llm=adapter)
    result = await graph.ainvoke({"event": persisted})

    assert isinstance(result["output"], EnrichmentOutput)
    assert result["fallback_used"] is True
    assert result["output"].recommendedSeverity == "HIGH"
    assert "camera cam_01" in result["output"].summary
