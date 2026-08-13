"""Authenticated EventCandidate ingest boundary for the CV producer."""

# Field names intentionally match the shared camelCase JSON contract.
# ruff: noqa: N815

import hmac
import os
from datetime import datetime
from typing import Literal

from app.services.ingest import CandidateReferenceError, IdempotencyConflict, ingest_event_candidate
from fastapi import APIRouter, Header, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator

router = APIRouter(prefix="/api/v1/events", tags=["Events Ingest"])


class ObservationData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    personCount: int = Field(default=0, ge=0, le=100000)
    dwellSeconds: float | None = Field(default=None, ge=0, le=86400, allow_inf_nan=False)
    insideZone: bool = False
    stationarySeconds: float | None = Field(default=None, ge=0, le=86400, allow_inf_nan=False)
    ownerAbsentSeconds: float | None = Field(default=None, ge=0, le=86400, allow_inf_nan=False)


class ArtifactData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available: bool = False
    contentType: str = Field(default="image/jpeg", max_length=100)
    redactionStatus: Literal["PENDING", "COMPLETE", "FAILED"] = "PENDING"
    uri: str | None = Field(default=None, max_length=2048)


class EventCandidateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidateId: str = Field(min_length=1, max_length=255, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    sourceEngine: Literal["CV", "VLM"] = "CV"
    cameraId: str = Field(min_length=1, max_length=50, pattern=r"^cam_[0-9]+$")
    zoneId: str | None = Field(default=None, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    sourceType: str = Field(default="SIMULATED", min_length=1, max_length=30, pattern=r"^[A-Za-z0-9_-]+$")
    eventType: Literal[
        "ZONE_INTRUSION",
        "CROWD_THRESHOLD",
        "ABANDONED_OBJECT",
        "SUSPECTED_FALL",
        "COVERAGE_DEGRADED",
    ]
    eventDetected: bool = True
    detectedAt: datetime
    firstSeenAt: datetime
    lastSeenAt: datetime
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    trackCount: int = Field(default=1, ge=0, le=100000)
    trackIds: list[int] = Field(default_factory=list, max_length=10000)
    bbox: list[float] | None = Field(default=None, max_length=4)
    observations: ObservationData
    modelVersion: str = Field(default="deimv2-phase7a", min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")
    ruleVersion: str = Field(default="intrusion-rule-v1", min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")
    policyVersion: int = Field(default=1, ge=1, le=1000000)
    artifact: ArtifactData = Field(default_factory=ArtifactData)

    @model_validator(mode="after")
    def validate_timestamps(self):
        if any(value.tzinfo is None or value.utcoffset() is None for value in
               (self.firstSeenAt, self.detectedAt, self.lastSeenAt)):
            raise ValueError("timestamps must include a timezone")
        if not (self.firstSeenAt <= self.detectedAt <= self.lastSeenAt):
            raise ValueError("timestamps must satisfy firstSeenAt <= detectedAt <= lastSeenAt")
        return self


class TelemetryTrackData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    trackId: int
    className: str = "person"
    confidence: float
    bbox: list[float]


class FrameTelemetryIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    cameraId: str
    timestamp: str
    videoTime: float | None = Field(default=None)
    frameSize: list[int] = Field(default_factory=lambda: [640, 480])
    tracks: list[TelemetryTrackData] = Field(default_factory=list)


def _authenticate(authorization: str | None) -> None:
    expected = os.getenv("EVENT_INGEST_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=401, detail="Producer credential not configured")
    supplied = authorization.removeprefix("Bearer ") if authorization and authorization.startswith("Bearer ") else ""
    if not authorization or not authorization.startswith("Bearer "):
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


@router.post("/telemetry", status_code=200)
async def ingest_telemetry(
    telemetry: FrameTelemetryIn,
    authorization: str | None = Header(default=None),
):
    _authenticate(authorization)
    from app.services.ingest import CAMERA_ID_MAP, manager
    mapped_id = 1
    if telemetry.cameraId in CAMERA_ID_MAP:
        mapped_id = CAMERA_ID_MAP[telemetry.cameraId]
    elif telemetry.cameraId.startswith("cam_"):
        try:
            mapped_id = int(telemetry.cameraId.split("_")[1])
        except (IndexError, ValueError):
            mapped_id = 1

    await manager.broadcast({
        "type": "FRAME_TELEMETRY",
        "cameraId": telemetry.cameraId,
        "numericCameraId": mapped_id,
        "timestamp": telemetry.timestamp,
        "videoTime": telemetry.videoTime,
        "frameSize": telemetry.frameSize,
        "tracks": [t.model_dump() for t in telemetry.tracks],
    })
    return {"status": "OK"}

