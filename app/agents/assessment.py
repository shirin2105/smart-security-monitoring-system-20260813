"""AgentAssessment: durable agent output at the Incident seam (SPEC §3.6).

The assessment is advisory only. It carries the agent's severity and
recommended action for a *persisted incident*, with provenance so every
field can be traced to a model/prompt version. Building an assessment
never mutates the incident or the event.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel

from app.common.schemas import EnrichmentOutput

SEVERITY_MAP = {
    "INFO": "low",
    "WARNING": "medium",
    "HIGH": "high",
    "CRITICAL": "critical",
}

# SPEC §9 action allow-list; the mapping is a deterministic fallback for
# enrichment outputs that do not carry an explicit action.
ACTION_MAP = {
    "low": "log_only",
    "medium": "notify_guard",
    "high": "request_guard_verification",
    "critical": "request_manager_review",
}

Severity = Literal["low", "medium", "high", "critical"]
RecommendedAction = Literal[
    "log_only",
    "notify_guard",
    "request_guard_verification",
    "request_manager_review",
    "request_alarm",
    "request_gate_lock",
]


class AgentAssessment(BaseModel):
    """Structured agent output attached to a persisted incident."""

    schema_version: str = "1.0"
    assessment_id: str
    incident_id: str
    event_type: str
    severity: Severity
    confidence: float = 0.0
    reason: str
    recommended_action: RecommendedAction
    requires_human_approval: bool = False
    model_name: str
    model_version: str = "configured-version"
    prompt_version: str = "assessment-v1"
    created_at: str


def build_assessment(
    *,
    incident_id: str,
    event_type: str,
    enrichment: EnrichmentOutput,
    model: str,
    confidence: float = 0.0,
    created_at: str | None = None,
) -> AgentAssessment:
    """Build an AgentAssessment from an enrichment output.

    The severity follows the SPEC §3.6 enum (low/medium/high/critical).
    Confidence comes from the event candidate, not the LLM.
    ``requires_human_approval`` is always False here: the deterministic
    policy (SPEC §10) decides approvals, never the agent.
    """
    severity = SEVERITY_MAP.get(enrichment.recommendedSeverity, "low")
    if event_type == "ABANDONED_OBJECT" and severity == "critical":
        severity = "high"

    now = created_at or datetime.now(UTC).isoformat()
    return AgentAssessment(
        assessment_id=f"assess-{uuid.uuid4()}",
        incident_id=incident_id,
        event_type=event_type,
        severity=severity,
        confidence=confidence,
        reason=enrichment.rationale,
        recommended_action=ACTION_MAP[severity],
        requires_human_approval=False,
        model_name=model,
        created_at=now,
    )
