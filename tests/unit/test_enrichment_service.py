"""EnrichmentService tests: event metadata → LLM output or deterministic fallback.

The service is the runtime glue between a persisted EventCandidate and the
enrichment graph. It must never raise on provider failure (FR-AI-07 fallback
semantics) and must never mutate the input event dict.
"""

import json

import pytest

from app.agents.fallback import build_fallback_output
from app.common.schemas import EnrichmentOutput, EventCandidate
from app.services.enrichment import EnrichmentService
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
    return json.dumps(
        {
            "recommendedSeverity": "HIGH",
            "rationale": "Person inside restricted zone beyond dwell",
            "summary": "Intrusion candidate at restricted_gate",
            "actionChecklist": ["Verify zone", "Check authorized personnel"],
        }
    )


def _candidate() -> EventCandidate:
    return EventCandidate(
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


@pytest.mark.asyncio
async def test_enrich_returns_valid_output_with_llm(tmp_path):
    service = EnrichmentService(
        output_dir=str(tmp_path), llm_adapter=_make_adapter(responses=[_valid_response()])
    )
    result = await service.enrich(_candidate())

    assert isinstance(result.output, EnrichmentOutput)
    assert result.output.recommendedSeverity == "HIGH"
    assert result.fallback_used is False
    assert result.error is None


@pytest.mark.asyncio
async def test_enrich_falls_back_without_llm(tmp_path):
    service = EnrichmentService(output_dir=str(tmp_path), llm_adapter=_make_adapter(available=False))
    result = await service.enrich(_candidate())

    assert isinstance(result.output, EnrichmentOutput)
    assert result.fallback_used is True
    assert result.error is not None
    assert result.output.recommendedSeverity == "HIGH"


@pytest.mark.asyncio
async def test_enrich_persists_result_json(tmp_path):
    service = EnrichmentService(
        output_dir=str(tmp_path), llm_adapter=_make_adapter(responses=[_valid_response()])
    )
    await service.enrich(_candidate())

    target = tmp_path / f"enrichment_{INTRUSION_EVENT['candidateId']}.json"
    assert target.exists()
    persisted = json.loads(target.read_text(encoding="utf-8"))
    assert persisted["candidateId"] == INTRUSION_EVENT["candidateId"]
    assert persisted["enrichment"]["recommendedSeverity"] == "HIGH"
    assert persisted["telemetry"]["fallbackUsed"] is False
    assert persisted["telemetry"]["outputValid"] is True


@pytest.mark.asyncio
async def test_enrich_persists_fallback_result(tmp_path):
    service = EnrichmentService(output_dir=str(tmp_path), llm_adapter=_make_adapter(available=False))
    await service.enrich(_candidate())

    target = tmp_path / f"enrichment_{INTRUSION_EVENT['candidateId']}.json"
    assert target.exists()
    persisted = json.loads(target.read_text(encoding="utf-8"))
    assert persisted["telemetry"]["fallbackUsed"] is True
    assert persisted["enrichment"]["rationale"].startswith("Fallback")


@pytest.mark.asyncio
async def test_enrich_never_mutates_input_candidate(tmp_path):
    import copy

    service = EnrichmentService(
        output_dir=str(tmp_path), llm_adapter=_make_adapter(responses=[_valid_response()])
    )
    candidate = _candidate()
    snapshot = copy.deepcopy(candidate.model_dump(mode="json"))
    await service.enrich(candidate)
    assert candidate.model_dump(mode="json") == snapshot


@pytest.mark.asyncio
async def test_enrich_persist_failure_does_not_raise(tmp_path):
    service = EnrichmentService(
        output_dir=str(tmp_path), llm_adapter=_make_adapter(responses=[_valid_response()])
    )
    candidate = _candidate()
    candidate.candidateId = 'bad"candidate"id'
    result = await service.enrich(candidate)
    assert isinstance(result.output, EnrichmentOutput)
    assert result.error is not None
    assert result.fallback_used is True


def test_fallback_output_caps_abandoned_object_at_high():
    event = dict(INTRUSION_EVENT, eventType="ABANDONED_OBJECT")
    output = build_fallback_output(event)
    assert output.recommendedSeverity in {"INFO", "WARNING", "HIGH"}


def test_fallback_output_other_event_types():
    suspected_fall = build_fallback_output(dict(INTRUSION_EVENT, eventType="SUSPECTED_FALL"))
    assert suspected_fall.recommendedSeverity == "WARNING"

    coverage_degraded = build_fallback_output(dict(INTRUSION_EVENT, eventType="COVERAGE_DEGRADED"))
    assert coverage_degraded.recommendedSeverity == "INFO"

    unknown = build_fallback_output(dict(INTRUSION_EVENT, eventType="UNKNOWN_TYPE"))
    assert unknown.recommendedSeverity == "INFO"
    assert unknown.actionChecklist  # falls back to the coverage checklist


def test_fallback_output_crowd_uses_track_count():
    crowd = build_fallback_output(dict(INTRUSION_EVENT, eventType="CROWD_THRESHOLD", trackCount=6))
    assert crowd.recommendedSeverity == "WARNING"
    assert "6" in crowd.summary


@pytest.mark.parametrize(
    ("event_type", "track_count", "expected_severity"),
    [
        ("ZONE_INTRUSION", 1, "HIGH"),
        ("CROWD_THRESHOLD", 12, "WARNING"),
        ("ABANDONED_OBJECT", 1, "HIGH"),
        ("SUSPECTED_FALL", 1, "WARNING"),
        ("COVERAGE_DEGRADED", 1, "INFO"),
    ],
)
@pytest.mark.asyncio
async def test_enrich_all_event_types_with_mock_llm(tmp_path, event_type, track_count, expected_severity):
    """Full service run (graph + LLM mock) across all supported event types."""
    candidate = EventCandidate(
        candidateId=f"mock-{event_type}-1",
        eventType=event_type,
        cameraId="cam_01",
        zoneId="restricted_gate",
        sourceType="SIMULATED",
        detectedAt="2026-07-29T10:15:30Z",
        firstSeenAt="2026-07-29T10:15:25Z",
        lastSeenAt="2026-07-29T10:15:30Z",
        confidence=0.88,
        trackCount=track_count,
        observations={"personCount": track_count, "dwellSeconds": 2.5, "insideZone": True},
    )
    mock_response = json.dumps(
        {
            "recommendedSeverity": expected_severity,
            "rationale": f"mock rationale for {event_type}",
            "summary": f"mock summary for {event_type}",
            "actionChecklist": ["Verify on camera"],
        }
    )
    service = EnrichmentService(
        output_dir=str(tmp_path), llm_adapter=_make_adapter(responses=[mock_response])
    )
    result = await service.enrich(candidate)

    assert result.fallback_used is False
    assert result.output.recommendedSeverity == expected_severity
    assert len(result.output.actionChecklist) <= 5
    persisted = json.loads(
        (tmp_path / f"enrichment_mock-{event_type}-1.json").read_text(encoding="utf-8")
    )
    assert persisted["telemetry"]["fallbackUsed"] is False
    assert persisted["telemetry"]["outputValid"] is True


@pytest.mark.parametrize(
    "event_type",
    ["ZONE_INTRUSION", "CROWD_THRESHOLD", "ABANDONED_OBJECT", "SUSPECTED_FALL", "COVERAGE_DEGRADED"],
)
@pytest.mark.asyncio
async def test_enrich_all_event_types_fallback(tmp_path, event_type):
    """Fallback path (no LLM) across all event types: severity caps + allow-list."""
    candidate = EventCandidate(
        candidateId=f"mock-fb-{event_type}-1",
        eventType=event_type,
        cameraId="cam_01",
        zoneId="restricted_gate",
        sourceType="SIMULATED",
        detectedAt="2026-07-29T10:15:30Z",
        firstSeenAt="2026-07-29T10:15:25Z",
        lastSeenAt="2026-07-29T10:15:30Z",
        confidence=0.88,
        trackCount=3,
        observations={"personCount": 3, "dwellSeconds": 2.5, "insideZone": True},
    )
    service = EnrichmentService(output_dir=str(tmp_path), llm_adapter=_make_adapter(available=False))
    result = await service.enrich(candidate)

    assert result.fallback_used is True
    assert result.error is not None
    if event_type == "ABANDONED_OBJECT":
        assert result.output.recommendedSeverity != "CRITICAL"
    assert len(result.output.actionChecklist) <= 5
    persisted = json.loads(
        (tmp_path / f"enrichment_mock-fb-{event_type}-1.json").read_text(encoding="utf-8")
    )
    assert persisted["telemetry"]["fallbackUsed"] is True
