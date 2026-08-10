"""AgentAssessment tests: SPEC §3.6 contract at the Incident seam.

The assessment is the durable agent output attached to a persisted incident:
schema_version, incident reference, event type, severity (low|medium|high|
critical), recommended_action from the SPEC §9 allow-list, and provenance
(model/prompt version). It is advisory only and never mutates the event.
"""

import json

from app.agents.assessment import build_assessment
from app.common.schemas import EnrichmentOutput


def _enrichment(severity: str) -> EnrichmentOutput:
    return EnrichmentOutput(
        recommendedSeverity=severity,
        rationale="rationale",
        summary="summary",
        actionChecklist=["Check area"],
    )


def test_build_assessment_maps_severity_and_action():
    assessment = build_assessment(
        incident_id="inc-1",
        event_type="ZONE_INTRUSION",
        enrichment=_enrichment("HIGH"),
        model="z-ai/glm-5.2",
    )

    assert assessment.schema_version == "1.0"
    assert assessment.incident_id == "inc-1"
    assert assessment.event_type == "ZONE_INTRUSION"
    assert assessment.severity == "high"
    assert assessment.recommended_action == "request_guard_verification"
    assert assessment.requires_human_approval is False
    assert assessment.model_name == "z-ai/glm-5.2"
    assert assessment.prompt_version == "assessment-v1"
    assert assessment.assessment_id
    assert assessment.created_at


def test_build_assessment_severity_mapping():
    cases = {
        "INFO": ("low", "log_only"),
        "WARNING": ("medium", "notify_guard"),
        "HIGH": ("high", "request_guard_verification"),
        "CRITICAL": ("critical", "request_manager_review"),
    }
    for severity, (expected_sev, expected_action) in cases.items():
        assessment = build_assessment(
            incident_id="inc-1",
            event_type="ZONE_INTRUSION",
            enrichment=_enrichment(severity),
            model="m",
        )
        assert assessment.severity == expected_sev
        assert assessment.recommended_action == expected_action


def test_assessment_abandoned_object_never_critical():
    assessment = build_assessment(
        incident_id="inc-1",
        event_type="ABANDONED_OBJECT",
        enrichment=_enrichment("HIGH"),
        model="m",
    )
    assert assessment.severity != "critical"


def test_assessment_json_roundtrip_matches_spec_fields():
    assessment = build_assessment(
        incident_id="inc-1",
        event_type="ZONE_INTRUSION",
        enrichment=_enrichment("HIGH"),
        model="m",
    )
    dumped = json.loads(assessment.model_dump_json())

    expected_fields = {
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
    assert set(dumped) == expected_fields
    assert dumped["recommended_action"] in {
        "log_only",
        "notify_guard",
        "request_guard_verification",
        "request_manager_review",
        "request_alarm",
        "request_gate_lock",
    }
