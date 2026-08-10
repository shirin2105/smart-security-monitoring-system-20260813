"""Deep assessment runner: typed outcome beside the legacy graph path.

``AssessmentRunner`` owns the compiled workflow (compiled once per
instance), the persistence handoff, and the typed outcome contract
(``AssessmentOutcome`` + ``AssessmentTelemetry``). Assessment is
advisory only: ``assess()`` never mutates the candidate, and persistence
failures are reported in the outcome instead of rewriting the result.
"""

from __future__ import annotations

from pathlib import Path

from app.agents._workflow import AssessmentWorkflow
from app.agents.assessment import AssessmentOutcome, AssessmentTelemetry, build_assessment
from app.common.schemas import EventCandidate
from app.llm.adapter import LLMAdapter
from app.services.assessment_record import AssessmentRecordStore, ProviderOutcome


class AssessmentRunner:
    def __init__(
        self,
        output_dir: str = "artifacts/backend_events",
        llm_adapter: LLMAdapter | None = None,
        enabled: bool = True,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.record_store = AssessmentRecordStore(str(self.output_dir))
        adapter = llm_adapter
        if adapter is None and enabled:
            from app.llm.adapter import create_llm_adapter

            adapter = create_llm_adapter()
        self._workflow = AssessmentWorkflow(adapter)

    async def assess(self, candidate: EventCandidate) -> AssessmentOutcome:
        state = await self._workflow.run(candidate.model_dump(mode="json"))
        fallback_used = bool(state.get("fallback_used"))
        raw_telemetry = state.get("telemetry") or {}
        provider_model = str(raw_telemetry.get("model", ""))
        telemetry = AssessmentTelemetry(
            provider_output_valid=bool(raw_telemetry.get("output_valid", False)),
            fallback_used=fallback_used,
            latency_ms=float(raw_telemetry.get("latency_ms", 0.0)),
            model_name=provider_model,
            provider_error=state.get("error"),
        )
        event_type = candidate.eventType.value
        assessment = build_assessment(
            incident_id=candidate.candidateId,
            event_type=event_type,
            enrichment=state["output"],
            model="deterministic-fallback" if fallback_used else provider_model,
            confidence=candidate.confidence,
        )
        persist_error = self.record_store.save(
            candidate_id=candidate.candidateId,
            event_type=event_type,
            assessment=assessment,
            provider=ProviderOutcome(
                output_valid=telemetry.provider_output_valid,
                fallback_used=telemetry.fallback_used,
                latency_ms=telemetry.latency_ms,
                model=telemetry.model_name,
                error=telemetry.provider_error,
            ),
        )
        return AssessmentOutcome(
            assessment=assessment,
            status="fallback" if fallback_used else "completed",
            telemetry=telemetry,
            persist_error=persist_error,
        )


def create_assessment_runner(
    output_dir: str = "artifacts/backend_events",
    llm_adapter: LLMAdapter | None = None,
    llm_enabled: bool | None = None,
) -> AssessmentRunner:
    from app.config import settings

    enabled = settings.llm_enabled if llm_enabled is None else llm_enabled
    return AssessmentRunner(output_dir=output_dir, llm_adapter=llm_adapter, enabled=enabled)
