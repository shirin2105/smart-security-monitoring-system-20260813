"""Ingest endpoint: CV pipeline (app/) POST EventCandidate vào backend."""

# Field names match the shared EventCandidate contract (camelCase JSON) from app/.
# ruff: noqa: N815

import logging

from app.services.ingest import ingest_event_candidate
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/api/v1/events", tags=["Events Ingest"])


class ObservationData(BaseModel):
    personCount: int = 0
    dwellSeconds: float | None = None
    insideZone: bool = False
    stationarySeconds: float | None = None
    ownerAbsentSeconds: float | None = None


class EventCandidateIn(BaseModel):
    candidateId: str = Field(min_length=1)
    cameraId: str
    eventType: str
    severity: str = "warning"
    description: str | None = None
    detectedAt: str | None = None
    bbox: list[float] | None = None
    observations: ObservationData | None = None


@router.post("/ingest", status_code=201)
async def ingest_event(candidate: EventCandidateIn):
    """Nhận EventCandidate từ CV worker, persist thành Incident + broadcast."""
    try:
        incident = await ingest_event_candidate(candidate.model_dump())
        return {"status": "ACCEPTED", "incident": incident}
    except Exception as e:
        logger.error(f"Ingest failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to ingest event candidate")
