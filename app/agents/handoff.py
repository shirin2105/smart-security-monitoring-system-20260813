import logging

from app.agents.assessment import AssessmentOutcome
from app.agents.runtime import AssessmentRunner
from app.common.schemas import EventCandidate

logger = logging.getLogger(__name__)


class AssessmentHandoff:
    def __init__(self, runner: AssessmentRunner) -> None:
        self.runner = runner

    async def run(self, candidate: EventCandidate) -> AssessmentOutcome | None:
        fields = {
            "candidate_id": candidate.candidateId,
            "event_type": candidate.eventType.value,
        }
        try:
            outcome = await self.runner.assess(candidate)
        except Exception as exc:
            logger.exception(
                "agent_assessment_failed",
                extra={
                    **fields,
                    "assessment_status": "failed",
                    "exception_class": type(exc).__name__,
                },
            )
            return None

        level = logging.ERROR if outcome.persist_error else logging.INFO
        logger.log(
            level,
            "agent_assessment_completed",
            extra={
                **fields,
                "assessment_status": outcome.status,
                "fallback_used": outcome.telemetry.fallback_used,
                "persist_error": outcome.persist_error,
            },
        )
        return outcome
