from fastapi import APIRouter
from app.config import settings
from app.sources.camera_health import CameraHealthMonitor

router = APIRouter(tags=["Health"])


@router.get("/health/live")
def health_live():
    """Returns status of worker process."""
    return {"status": "ALIVE"}


@router.get("/health/ready")
def health_ready():
    """Checks config validity and readiness."""
    cameras = settings.cameras
    zones = settings.zones
    return {
        "status": "READY",
        "configured_cameras": len(cameras),
        "configured_zones": len(zones),
    }


@router.get("/api/v1/cameras/{camera_id}/health")
def camera_health(camera_id: str):
    """Returns camera health status metrics."""
    monitor = CameraHealthMonitor(camera_id=camera_id)
    return monitor.get_status()
