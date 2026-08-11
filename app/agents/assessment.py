"""AgentAssessment: durable agent output at the Incident seam (SPEC §3.6).

The assessment is advisory only. It carries the agent's severity and
recommended action for a *persisted incident*, with provenance so every
field can be traced to a model/prompt version. Building an assessment
never mutates the incident or the event.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

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


AssessmentStatus = Literal["completed", "fallback"]


class AssessmentTelemetry(BaseModel):
    provider_output_valid: bool
    fallback_used: bool
    latency_ms: float
    model_name: str
    provider_error: str | None = None


class AssessmentOutcome(BaseModel):
    assessment: AgentAssessment
    status: AssessmentStatus
    telemetry: AssessmentTelemetry
    persist_error: str | None = None
