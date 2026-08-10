import uuid
from datetime import UTC, datetime

from app.agents.assessment import AgentAssessment
from app.agents.provider import ProviderDraft
from app.common.schemas import EventCandidate

SEVERITY_MAP = {
    "INFO": "low",
    "WARNING": "medium",
    "HIGH": "high",
    "CRITICAL": "critical",
}
ACTION_MAP = {
    "low": "log_only",
    "medium": "notify_guard",
    "high": "request_guard_verification",
    "critical": "request_manager_review",
}
FALLBACK_SEVERITY = {
    "ZONE_INTRUSION": "HIGH",
    "CROWD_THRESHOLD": "WARNING",
    "ABANDONED_OBJECT": "HIGH",
    "SUSPECTED_FALL": "WARNING",
    "COVERAGE_DEGRADED": "INFO",
}


def fallback_draft(candidate: EventCandidate, *, reason: str) -> ProviderDraft:
    event_type = candidate.eventType.value
    return ProviderDraft(
        recommendedSeverity=FALLBACK_SEVERITY.get(event_type, "INFO"),
        rationale=f"Fallback rule-based cho {event_type}: {reason}.",
    )


def build_agent_assessment(
    *,
    candidate: EventCandidate,
    draft: ProviderDraft,
    model_name: str,
    prompt_version: str,
    created_at: str | None = None,
    assessment_id: str | None = None,
) -> AgentAssessment:
    severity = SEVERITY_MAP[draft.recommended_severity]
    if candidate.eventType.value == "ABANDONED_OBJECT" and severity == "critical":
        severity = "high"
    return AgentAssessment(
        assessment_id=assessment_id or f"assess-{uuid.uuid4()}",
        incident_id=candidate.candidateId,
        event_type=candidate.eventType.value,
        severity=severity,
        confidence=candidate.confidence,
        reason=draft.rationale,
        recommended_action=ACTION_MAP[severity],
        requires_human_approval=False,
        model_name=model_name,
        prompt_version=prompt_version,
        created_at=created_at or datetime.now(UTC).isoformat(),
    )
