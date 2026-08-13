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
from app.agents.assessment import AssessmentOutcome, AssessmentTelemetry
from app.agents.policy import build_agent_assessment
from app.agents.record import AssessmentRecord, AssessmentRecordStore
from app.common.schemas import EventCandidate
from app.llm.adapter import LLMAdapter


class AssessmentRunner:
    def __init__(
        self,
        output_dir: str = "artifacts/backend_events",
        llm_adapter: LLMAdapter | None = None,
        enabled: bool = True,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.record_store = AssessmentRecordStore(str(self.output_dir))
        provider = llm_adapter
        if provider is None and enabled:
            from app.llm.adapter import create_llm_adapter

            provider = create_llm_adapter()
        self._provider_enabled = provider is not None
        self._workflow = AssessmentWorkflow(provider)

    async def assess(self, candidate: EventCandidate) -> AssessmentOutcome:
        state = await self._workflow.run(candidate)
        provider_result = state["provider_result"]
        fallback_used = bool(state["fallback_used"])
        assessment = build_agent_assessment(
            candidate=candidate,
            draft=state["draft"],
            model_name="deterministic-fallback" if fallback_used else provider_result.model_name,
            prompt_version="assessment-v2",
        )
        telemetry = AssessmentTelemetry(
            provider_output_valid=provider_result.draft is not None,
            fallback_used=fallback_used,
            latency_ms=provider_result.latency_ms,
            model_name=provider_result.model_name if self._provider_enabled else "",
            provider_error=provider_result.error,
        )
        outcome = AssessmentOutcome(
            assessment=assessment,
            status="fallback" if fallback_used else "completed",
            telemetry=telemetry,
        )

        persist_error = self.record_store.save(AssessmentRecord.from_outcome(candidate=candidate, outcome=outcome))
        return outcome.model_copy(update={"persist_error": persist_error})


def create_assessment_runner(
    output_dir: str = "artifacts/backend_events",
    llm_adapter: LLMAdapter | None = None,
    llm_enabled: bool | None = None,
) -> AssessmentRunner:
    from app.config import settings

    enabled = settings.llm_enabled if llm_enabled is None else llm_enabled
    return AssessmentRunner(output_dir=output_dir, llm_adapter=llm_adapter, enabled=enabled)
