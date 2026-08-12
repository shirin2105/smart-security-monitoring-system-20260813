"""Authenticated EventCandidate ingest boundary for the CV producer."""

# Field names intentionally match the shared camelCase JSON contract.
# ruff: noqa: N815

import hmac
import os
from typing import Literal

from app.services.ingest import CandidateReferenceError, IdempotencyConflict, ingest_event_candidate
from fastapi import APIRouter, Header, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/api/v1/events", tags=["Events Ingest"])


class ObservationData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    personCount: int = 0
    dwellSeconds: float | None = None
    insideZone: bool = False
    stationarySeconds: float | None = None
    ownerAbsentSeconds: float | None = None


class ArtifactData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available: bool = False
    contentType: str = "image/jpeg"
    redactionStatus: Literal["PENDING", "COMPLETE", "FAILED"] = "PENDING"
    uri: str | None = None


class EventCandidateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidateId: str = Field(min_length=1, max_length=255)
    sourceEngine: Literal["CV", "VLM"] = "CV"
    cameraId: str
    zoneId: str | None = None
    sourceType: str = "SIMULATED"
    eventType: Literal[
        "ZONE_INTRUSION",
        "CROWD_THRESHOLD",
        "ABANDONED_OBJECT",
        "SUSPECTED_FALL",
        "COVERAGE_DEGRADED",
    ]
    eventDetected: bool = True
    detectedAt: str
    firstSeenAt: str
    lastSeenAt: str
    confidence: float
    trackCount: int = 1
    trackIds: list[int] = Field(default_factory=list)
    observations: ObservationData
    modelVersion: str = "deimv2-phase7a"
    ruleVersion: str = "intrusion-rule-v1"
    policyVersion: int = 1
    artifact: ArtifactData = Field(default_factory=ArtifactData)


def _authenticate(authorization: str | None) -> None:
    expected = os.getenv("EVENT_INGEST_TOKEN", "")
    supplied = authorization.removeprefix("Bearer ") if authorization else ""
    if not expected or not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid producer credential")
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Invalid producer credential")


@router.post("/ingest", status_code=201)
async def ingest_event(
    candidate: EventCandidateIn,
    response: Response,
    authorization: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    _authenticate(authorization)
    if idempotency_key and idempotency_key != candidate.candidateId:
        raise HTTPException(status_code=409, detail="Idempotency key does not match candidate")
    try:
        result = await ingest_event_candidate(candidate.model_dump(mode="json"))
    except IdempotencyConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except CandidateReferenceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result["status"] == "DUPLICATE_IGNORED":
        response.status_code = 200
    return result
