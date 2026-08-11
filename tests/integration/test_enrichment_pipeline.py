"""Integration: persisted candidate JSON → assessment runner → valid output or fallback."""

import json

import pytest

from app.agents import AssessmentRunner
from app.common.schemas import EventCandidate
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

VALID_LLM_RESPONSE = json.dumps({
    "recommendedSeverity": "HIGH",
    "rationale": "Person inside restricted zone beyond dwell",
})


def _persisted_candidate_payload() -> dict:
    return EventCandidate.model_validate(INTRUSION_EVENT).model_dump(mode="json")


def test_candidate_dump_roundtrip_matches_backend_ingest(tmp_path):
    """Backend persists EventCandidate as JSON; the agent consumes that JSON."""
    persisted = _persisted_candidate_payload()
    file_path = tmp_path / "candidate.json"
    file_path.write_text(json.dumps(persisted, ensure_ascii=False), encoding="utf-8")

    loaded = json.loads(file_path.read_text(encoding="utf-8"))
    revalidated = EventCandidate.model_validate(loaded)
    assert revalidated.candidateId == INTRUSION_EVENT["candidateId"]
    assert revalidated.eventType.value == "ZONE_INTRUSION"


@pytest.mark.asyncio
async def test_enrichment_from_persisted_json_with_llm(tmp_path):
    candidate = EventCandidate.model_validate(_persisted_candidate_payload())
    runner = AssessmentRunner(
        output_dir=str(tmp_path),
        llm_adapter=_make_adapter(responses=[VALID_LLM_RESPONSE]),
    )

    outcome = await runner.assess(candidate)

    assert outcome.status == "completed"
    assert outcome.assessment.severity == "high"
    assert outcome.telemetry.provider_output_valid is True


@pytest.mark.asyncio
async def test_enrichment_fallback_when_llm_outage(tmp_path):
    candidate = EventCandidate.model_validate(_persisted_candidate_payload())
    runner = AssessmentRunner(
        output_dir=str(tmp_path),
        llm_adapter=_make_adapter(available=False),
    )

    outcome = await runner.assess(candidate)

    assert outcome.status == "fallback"
    assert outcome.assessment.severity == "high"
    assert outcome.telemetry.provider_output_valid is False
