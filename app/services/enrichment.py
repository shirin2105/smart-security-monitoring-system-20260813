"""Runtime enrichment service: persisted EventCandidate → AgentAssessment.

Owns the enrichment graph invocation for the ingest pipeline (FR-AI-07).
Advisory only: the output never mutates the candidate's severity or state.
Any provider failure or persist error resolves to a fallback result instead
of raising, so the ingest boundary is never blocked by the agent.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.agents.assessment import AgentAssessment, build_assessment
from app.agents.fallback import build_fallback_output
from app.agents.graph import build_enrichment_graph
from app.common.schemas import EnrichmentOutput
from app.llm.adapter import LLMAdapter
from app.services.assessment_record import AssessmentRecordStore, ProviderOutcome


@dataclass
class EnrichmentResult:
    assessment: AgentAssessment
    fallback_used: bool
    error: str | None
    telemetry: dict[str, Any] | None


def create_enrichment_service(
    output_dir: str = "artifacts/backend_events",
    llm_adapter: LLMAdapter | None = None,
    llm_enabled: bool | None = None,
) -> EnrichmentService:
    """Composition root: build the service from validated config (C5).

    Both the ingest route and the CLI construct their runtime through this
    factory, so config (``settings.llm_enabled``), adapters, and storage are
    assembled once. Tests inject an adapter directly.
    """
    from app.config import settings

    if llm_enabled is None:
        llm_enabled = settings.llm_enabled
    return EnrichmentService(
        output_dir=output_dir,
        llm_adapter=llm_adapter,
        enabled=llm_enabled,
    )


class EnrichmentService:
    """Enriches event candidates and persists the advisory result."""

    def __init__(
        self,
        output_dir: str = "artifacts/backend_events",
        llm_adapter: LLMAdapter | None = None,
        enabled: bool = True,
    ):
        self.output_dir = Path(output_dir)
        self.llm_adapter = llm_adapter
        self.enabled = enabled
        self.record_store = AssessmentRecordStore(str(self.output_dir))

    def _adapter(self) -> LLMAdapter | None:
        if self.llm_adapter is not None:
            return self.llm_adapter
        if self.enabled:
            from app.llm.adapter import create_llm_adapter

            return create_llm_adapter()
        return None

    async def enrich(self, candidate: Any) -> EnrichmentResult:
        """Run the enrichment graph on one candidate and persist the result.

        Returns the validated AgentAssessment (SPEC §3.6) as the canonical
        domain result. Never raises: provider failure, missing credentials,
        and persist errors all resolve to a deterministic fallback (FR-AI-06).
        """
        event = candidate.model_dump(mode="json")
        adapter = self._adapter()
        graph = build_enrichment_graph(llm=adapter)
        result = await graph.ainvoke({"event": event})

        output: EnrichmentOutput = result["output"]
        fallback_used = bool(result.get("fallback_used"))
        error = result.get("error")
        telemetry = result.get("telemetry")
        model = (telemetry or {}).get("model", "")
        output_valid = bool((telemetry or {}).get("output_valid", fallback_used))

        event_type = getattr(candidate, "eventType", "")
        event_type_value = event_type.value if hasattr(event_type, "value") else str(event_type)

        assessment = build_assessment(
            incident_id=str(getattr(candidate, "candidateId", "unknown")),
            event_type=event_type_value,
            enrichment=output,
            model=model,
            confidence=float(getattr(candidate, "confidence", 0.0) or 0.0),
        )

        provider = ProviderOutcome(
            output_valid=output_valid,
            fallback_used=fallback_used,
            latency_ms=(telemetry or {}).get("latency_ms", 0.0),
            model=model,
            error=error,
        )
        persist_error = self.record_store.save(
            candidate_id=str(getattr(candidate, "candidateId", "unknown")),
            event_type=event_type_value,
            assessment=assessment,
            provider=provider,
        )
        if persist_error is not None:
            error = persist_error

        return EnrichmentResult(
            assessment=assessment,
            fallback_used=fallback_used,
            error=error,
            telemetry=telemetry,
        )


def fallback_for_test(event: dict) -> EnrichmentOutput:
    """Deterministic fallback, exported for tests and evaluation tooling."""
    return build_fallback_output(event)
