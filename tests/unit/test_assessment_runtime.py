"""AssessmentRunner public-interface tests (Slice 1).

The runner is the deep path beside the legacy graph. These tests pin the
typed outcome contract: completed vs fallback status, telemetry provenance,
persistence, and the advisory-only invariant (never mutates the candidate).
"""

import copy
import json

import pytest

from app.agents import AssessmentRunner
from app.common.schemas import EventCandidate
from tests.unit.test_llm_adapter import _make_adapter


def _candidate(event_type: str = "ZONE_INTRUSION") -> EventCandidate:
    return EventCandidate(
        candidateId=f"candidate-{event_type}",
        eventType=event_type,
        cameraId="cam_01",
        zoneId="restricted_gate",
        sourceType="SIMULATED",
        detectedAt="2026-08-10T01:00:00Z",
        firstSeenAt="2026-08-10T00:59:58Z",
        lastSeenAt="2026-08-10T01:00:00Z",
        confidence=0.88,
        trackCount=1,
        observations={"personCount": 1, "dwellSeconds": 2.0, "insideZone": True},
    )


def _provider_response(severity: str = "HIGH") -> str:
    return json.dumps(
        {
            "recommendedSeverity": severity,
            "rationale": "controlled provider rationale",
            "summary": "legacy field removed in Slice 2",
            "actionChecklist": [],
        }
    )


@pytest.mark.asyncio
async def test_runner_returns_typed_completed_outcome(tmp_path):
    runner = AssessmentRunner(
        output_dir=str(tmp_path),
        llm_adapter=_make_adapter(responses=[_provider_response()]),
    )

    outcome = await runner.assess(_candidate())

    assert outcome.status == "completed"
    assert outcome.assessment.severity == "high"
    assert outcome.telemetry.provider_output_valid is True
    assert outcome.telemetry.fallback_used is False
    assert outcome.persist_error is None
    assert (tmp_path / "enrichment_candidate-ZONE_INTRUSION.json").exists()


@pytest.mark.asyncio
async def test_runner_returns_typed_fallback_without_provider(tmp_path):
    runner = AssessmentRunner(
        output_dir=str(tmp_path),
        llm_adapter=_make_adapter(available=False),
    )

    outcome = await runner.assess(_candidate())

    assert outcome.status == "fallback"
    assert outcome.assessment.model_name == "deterministic-fallback"
    assert outcome.telemetry.provider_output_valid is False
    assert outcome.telemetry.fallback_used is True


@pytest.mark.asyncio
async def test_runner_falls_back_for_malformed_provider_output(tmp_path):
    runner = AssessmentRunner(
        output_dir=str(tmp_path),
        llm_adapter=_make_adapter(responses=["not json"]),
    )

    outcome = await runner.assess(_candidate())

    assert outcome.status == "fallback"
    assert outcome.telemetry.provider_output_valid is False
    assert outcome.telemetry.provider_error is not None


@pytest.mark.parametrize(
    ("event_type", "provider_severity", "expected_severity"),
    [
        ("ZONE_INTRUSION", "HIGH", "high"),
        ("CROWD_THRESHOLD", "WARNING", "medium"),
        ("ABANDONED_OBJECT", "HIGH", "high"),
        ("SUSPECTED_FALL", "WARNING", "medium"),
        ("COVERAGE_DEGRADED", "INFO", "low"),
    ],
)
@pytest.mark.asyncio
async def test_runner_covers_all_event_types(
    tmp_path, event_type, provider_severity, expected_severity
):
    runner = AssessmentRunner(
        output_dir=str(tmp_path),
        llm_adapter=_make_adapter(responses=[_provider_response(provider_severity)]),
    )

    outcome = await runner.assess(_candidate(event_type))

    assert outcome.assessment.severity == expected_severity


@pytest.mark.asyncio
async def test_runner_never_mutates_candidate_and_reuses_instance(tmp_path):
    runner = AssessmentRunner(
        output_dir=str(tmp_path),
        llm_adapter=_make_adapter(responses=[_provider_response(), _provider_response("WARNING")]),
    )
    candidate = _candidate()
    snapshot = copy.deepcopy(candidate.model_dump(mode="json"))

    first = await runner.assess(candidate)
    second = await runner.assess(candidate.model_copy(update={"candidateId": "candidate-second"}))

    assert candidate.model_dump(mode="json") == snapshot
    assert first.assessment.severity == "high"
    assert second.assessment.severity == "medium"
