import os
import json
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, status
from app.common.schemas import EventCandidate
from app.common.idempotency import IdempotencyStore
from app.services.enrichment import EnrichmentService

router = APIRouter(prefix="/internal/api/v1", tags=["Events Ingestion"])
idempotency_store = IdempotencyStore(storage_file="artifacts/backend_events/idempotency.json")
BACKEND_EVENT_DIR = "artifacts/backend_events"

enrichment_service = EnrichmentService(output_dir=BACKEND_EVENT_DIR)


@router.post("/event-candidates", status_code=status.HTTP_201_CREATED)
async def ingest_event_candidate(
    candidate: EventCandidate,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    """
    Backend boundary endpoint receiving EventCandidate from CV or VLM workers.
    Enforces idempotency, persists candidates, then runs agent enrichment
    (advisory only; enrichment failure never fails ingestion — FR-AI-07).
    """
    candidate_id = idempotency_key or candidate.candidateId

    # Check idempotency
    if idempotency_store.is_processed(candidate_id):
        return {
            "status": "DUPLICATE_IGNORED",
            "candidateId": candidate_id,
            "message": "Candidate already processed and persisted.",
        }

    # Persist event candidate
    os.makedirs(BACKEND_EVENT_DIR, exist_ok=True)
    file_path = os.path.join(BACKEND_EVENT_DIR, f"candidate_{candidate_id}.json")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(candidate.model_dump(mode="json"), f, indent=2, ensure_ascii=False)

        idempotency_store.mark_processed(candidate_id)

        # Agent enrichment: advisory, best-effort, never blocks ingestion.
        try:
            enrichment = await enrichment_service.enrich(candidate)
        except Exception:
            enrichment = None

        response = {
            "status": "ACCEPTED",
            "candidateId": candidate_id,
            "stored_uri": f"/backend/events/candidate_{candidate_id}.json",
        }
        if enrichment is not None:
            response["enrichment"] = {
                "recommendedSeverity": enrichment.output.recommendedSeverity,
                "fallback_used": enrichment.fallback_used,
                "error": enrichment.error,
            }
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist event candidate: {str(e)}",
        )
