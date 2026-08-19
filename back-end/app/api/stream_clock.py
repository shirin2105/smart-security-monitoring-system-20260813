"""Live-stream clock boundary: the CV producer registers its loop epoch here and
the frontend reads it to keep every camera video in phase with the model."""

import os

from app.api.events_ingest import _authenticate
from app.services.ingest import CandidateReferenceError, map_camera_id
from app.services.stream_clock import get_stream_clocks, set_stream_clock
from app.db.database import SessionLocal
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/api/v1/stream", tags=["Stream Clock"])


class StreamClockIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cameraId: str = Field(min_length=1, max_length=50, pattern=r"^cam_[0-9]+$")
    epoch: float = Field(gt=0, le=4102444800)
    duration: float = Field(gt=0, le=86400)


@router.post("/clock", status_code=200)
def post_stream_clock(
    body: StreamClockIn,
    authorization: str | None = Header(default=None),
):
    """Register the wall-clock epoch + source duration for a camera's live loop."""
    _authenticate(authorization)
    db = SessionLocal()
    try:
        try:
            camera_id = map_camera_id(body.cameraId, db)
        except CandidateReferenceError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        db.close()
    set_stream_clock(camera_id, body.epoch, body.duration)
    return {"camera_id": camera_id, "epoch": body.epoch, "duration": body.duration}


@router.get("/clock", response_model=list[dict])
def list_stream_clocks():
    """Return every registered camera clock so the frontend can sync playhead."""
    return get_stream_clocks()