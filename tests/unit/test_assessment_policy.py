from enum import StrEnum

import pytest
from pydantic import ValidationError

from app.agents.policy import build_agent_assessment, fallback_draft
from app.agents.provider import ProviderDraft
from tests.unit.test_assessment_runtime import _candidate


@pytest.mark.parametrize(
    ("provider_severity", "expected_severity", "expected_action"),
    [
        ("INFO", "low", "log_only"),
        ("WARNING", "medium", "notify_guard"),
        ("HIGH", "high", "request_guard_verification"),
        ("CRITICAL", "critical", "request_manager_review"),
    ],
)
def test_policy_maps_severity_and_action(provider_severity, expected_severity, expected_action):
    assessment = build_agent_assessment(
        candidate=_candidate(),
        draft=ProviderDraft(
            recommendedSeverity=provider_severity,
            rationale="fact-based rationale",
        ),
        model_name="test-model",
        prompt_version="assessment-v2",
        created_at="2026-08-10T02:00:04Z",
        assessment_id="assess-fixed",
    )

    assert assessment.severity == expected_severity
    assert assessment.recommended_action == expected_action
    assert assessment.requires_human_approval is False
    assert assessment.confidence == 0.88


def test_abandoned_object_is_capped_at_high():
    assessment = build_agent_assessment(
        candidate=_candidate("ABANDONED_OBJECT"),
        draft=ProviderDraft(recommendedSeverity="CRITICAL", rationale="r"),
        model_name="test-model",
        prompt_version="assessment-v2",
    )

    assert assessment.severity == "high"
    assert assessment.recommended_action == "request_guard_verification"


def test_assessment_contract_keeps_exact_spec_fields():
    assessment = build_agent_assessment(
        candidate=_candidate(),
        draft=ProviderDraft(recommendedSeverity="HIGH", rationale="r"),
        model_name="test-model",
        prompt_version="assessment-v2",
        created_at="2026-08-10T02:00:04Z",
        assessment_id="assess-fixed",
    )

    assert set(assessment.model_dump()) == {
        "schema_version",
        "assessment_id",
        "incident_id",
        "event_type",
        "severity",
        "confidence",
        "reason",
        "recommended_action",
        "requires_human_approval",
        "model_name",
        "model_version",
        "prompt_version",
        "created_at",
    }
    assert assessment.recommended_action not in {"request_alarm", "request_gate_lock"}


@pytest.mark.parametrize(
    ("event_type", "expected"),
    [
        ("ZONE_INTRUSION", "HIGH"),
        ("CROWD_THRESHOLD", "WARNING"),
        ("ABANDONED_OBJECT", "HIGH"),
        ("SUSPECTED_FALL", "WARNING"),
        ("COVERAGE_DEGRADED", "INFO"),
    ],
)
def test_fallback_severity_is_fixed_by_event_type(event_type, expected):
    draft = fallback_draft(_candidate(event_type), reason="llm_unavailable")
    assert draft.recommended_severity == expected
    assert event_type in draft.rationale


def test_fallback_severity_defaults_to_info_for_unknown_event_type():
    class _UnknownEventType(StrEnum):
        NEW_EVENT = "NEW_EVENT"

    candidate = _candidate()
    candidate.eventType = _UnknownEventType.NEW_EVENT

    draft = fallback_draft(candidate, reason="llm_unavailable")
    assert draft.recommended_severity == "INFO"
    assert "NEW_EVENT" in draft.rationale


def test_provider_draft_rejects_removed_fields():
    with pytest.raises(ValidationError):
        ProviderDraft.model_validate(
            {
                "recommendedSeverity": "HIGH",
                "rationale": "r",
                "summary": "removed",
                "actionChecklist": [],
            }
        )
