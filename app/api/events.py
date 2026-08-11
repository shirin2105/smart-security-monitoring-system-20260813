from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status

from app.agents.handoff import AssessmentHandoff
from app.common.schemas import EventCandidate
from app.services.intake import PersistedIntake

router = APIRouter(prefix="/internal/api/v1", tags=["Events Ingestion"])


def get_intake(request: Request) -> PersistedIntake:
    return request.app.state.intake


def get_assessment_handoff(request: Request) -> AssessmentHandoff:
    return request.app.state.assessment_handoff


@router.post("/event-candidates", status_code=status.HTTP_201_CREATED)
def ingest_event_candidate(
    candidate: EventCandidate,
    background_tasks: BackgroundTasks,
    intake: Annotated[PersistedIntake, Depends(get_intake)],
    handoff: Annotated[AssessmentHandoff, Depends(get_assessment_handoff)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Backend boundary receiving EventCandidate from CV or VLM workers.

    Delegates identity, dedupe, and durable write to ``PersistedIntake``,
    then schedules agent enrichment as a background task — the response
    never blocks on the external LLM (architecture review candidates 4-5).
    """
    outcome = intake.accept(candidate, header_id=idempotency_key)
    if outcome.status == "ERROR":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=outcome.error or "Failed to persist event candidate",
        )
    if outcome.status == "ACCEPTED":
        canonical = intake.canonical_candidate(candidate, header_id=idempotency_key)
        background_tasks.add_task(handoff.run, canonical)
    return outcome.as_response()
