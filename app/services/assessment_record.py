"""Assessment record: one authoritative, typed JSON record per candidate.

Owns the persistence format and its reload/evaluation projection (C3).
``output_valid`` reflects whether the provider returned a schema-valid
result; a persist failure is reported as its own outcome and never
rewrites ``fallback_used``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.agents.assessment import AgentAssessment

ENRICHMENT_PREFIX = "enrichment_"
ENRICHMENT_SUFFIX = ".json"


@dataclass
class ProviderOutcome:
    """What the provider path produced, independent of persistence."""

    output_valid: bool
    fallback_used: bool
    latency_ms: float
    model: str
    error: str | None = None


class AssessmentRecordStore:
    """Persist and reload AgentAssessment records on the local filesystem."""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)

    def save(
        self,
        *,
        candidate_id: str,
        event_type: str,
        assessment: AgentAssessment,
        provider: ProviderOutcome,
        persist_error: str | None = None,
    ) -> str | None:
        """Write one record; returns an error string on failure, else None."""
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            record = {
                "candidateId": candidate_id,
                "eventType": event_type,
                "assessment": assessment.model_dump(mode="json"),
                "telemetry": {
                    "latencyMs": provider.latency_ms,
                    "model": provider.model,
                    "fallbackUsed": provider.fallback_used,
                    "outputValid": provider.output_valid,
                    "error": provider.error,
                    "persistError": persist_error,
                },
            }
            target = self.output_dir / f"{ENRICHMENT_PREFIX}{candidate_id}{ENRICHMENT_SUFFIX}"
            with open(target, "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2, ensure_ascii=False)
            return None
        except OSError as exc:
            return f"enrichment_persist_failed:{type(exc).__name__}"

    def load(self, candidate_id: str) -> dict[str, Any] | None:
        target = self.output_dir / f"{ENRICHMENT_PREFIX}{candidate_id}{ENRICHMENT_SUFFIX}"
        if not target.exists():
            return None
        try:
            return json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
