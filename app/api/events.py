
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, status

from app.common.schemas import EventCandidate
from app.services.enrichment import EnrichmentService
from app.services.intake import PersistedIntake

router = APIRouter(prefix="/internal/api/v1", tags=["Events Ingestion"])

BACKEND_EVENT_DIR = "artifacts/backend_events"

intake = PersistedIntake(storage_dir=BACKEND_EVENT_DIR)
enrichment_service = EnrichmentService(output_dir=BACKEND_EVENT_DIR)


async def _enrich_in_background(candidate: EventCandidate) -> None:
    """Run agent enrichment after the ingest response is sent.

    Advisory and best-effort (FR-AI-07): any failure is resolved by the
    service's fallback; it never affects the persisted candidate.
    """
    try:
        await enrichment_service.enrich(candidate)
    except Exception:
        pass


@router.post("/event-candidates", status_code=status.HTTP_201_CREATED)
def ingest_event_candidate(
    candidate: EventCandidate,
    background_tasks: BackgroundTasks,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
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
        background_tasks.add_task(_enrich_in_background, candidate)
    return outcome.as_response()
