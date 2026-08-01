from fastapi import APIRouter
from app.config import settings

router = APIRouter(prefix="/api/v1/debug", tags=["Debug"])


@router.get("/tracks/{camera_id}")
def get_debug_tracks(camera_id: str):
    """Local development debug endpoint returning track metadata without raw images."""
    return {
        "camera_id": camera_id,
        "active_tracks_count": 0,
        "note": "Debug metadata endpoint active",
    }
