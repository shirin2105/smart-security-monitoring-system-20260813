"""Ingest EventCandidate từ CV pipeline (app/) vào Incident storage.

Nối hai mảng: CV worker publish EventCandidate qua HTTP tới backend API.
Event type/severity/camera map sang schema cũ của backend (xam_nhap, warning...)
để frontend adapter hiện tại đọc được.
"""

import logging
from datetime import UTC, datetime

from app.db.database import SessionLocal
from app.db.models import Camera, Incident
from app.services.websocket import manager

logger = logging.getLogger("uvicorn.error")

# EventCandidate eventType (app/) -> event_type schema backend
EVENT_TYPE_MAP = {
    "ZONE_INTRUSION": "xam_nhap",
    "CROWD_THRESHOLD": "dam_dong",
    "ABANDONED_OBJECT": "vat_the_bo_quen",
    "SUSPECTED_FALL": "te_nga",
}

# EventCandidate severity -> schema backend
SEVERITY_MAP = {
    "CRITICAL": "critical",
    "HIGH": "high",
    "WARNING": "warning",
    "INFO": "warning",
}

# cameraId (app/, cam_01) -> camera id (backend, int)
CAMERA_ID_MAP = {
    "cam_01": 1,
    "cam_02": 2,
}


def map_event_type(event_type: str) -> str:
    return EVENT_TYPE_MAP.get(event_type, "xam_nhap")


def map_severity(severity: str) -> str:
    return SEVERITY_MAP.get(str(severity).upper(), "warning")


def map_camera_id(camera_id: str, db) -> int:
    """Map cameraId string sang id backend; fallback: cam_N -> N, rồi camera đầu tiên."""
    if camera_id in CAMERA_ID_MAP:
        return CAMERA_ID_MAP[camera_id]
    if camera_id.startswith("cam_"):
        try:
            return int(camera_id.split("_")[1])
        except (IndexError, ValueError):
            pass
    first = db.query(Camera).order_by(Camera.id.asc()).first()
    return first.id if first else 1


async def ingest_event_candidate(payload: dict) -> dict:
    """Persist EventCandidate thành Incident + broadcast qua WebSocket."""
    db = SessionLocal()
    try:
        camera_id = map_camera_id(payload.get("cameraId", ""), db)
        event_type = map_event_type(payload.get("eventType", "ZONE_INTRUSION"))
        severity = map_severity(payload.get("severity", "warning"))
        description = _build_description(payload, camera_id, event_type, severity)

        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        camera_name = camera.name if camera else f"Camera #{camera_id}"

        incident = Incident(
            camera_id=camera_id,
            event_type=event_type,
            severity=severity,
            description=description,
            status="pending",
            source="CV",
            created_at=datetime.now(UTC),
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)

        alert_payload = {
            "type": "NEW_ALERT",
            "incident": {
                "id": incident.id,
                "camera_id": incident.camera_id,
                "camera_name": camera_name,
                "event_type": incident.event_type,
                "severity": incident.severity,
                "description": incident.description,
                "status": incident.status,
                "source": "CV",
                "created_at": incident.created_at.isoformat(),
                "bbox": payload.get("bbox"),
            },
        }

        await manager.broadcast(alert_payload)
        logger.info(
            f"Ingested EventCandidate -> Incident #{incident.id}: {incident.description}"
        )
        return alert_payload["incident"]
    except Exception as e:
        logger.error(f"Failed to ingest EventCandidate: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def _build_description(payload: dict, camera_id: int, event_type: str, severity: str) -> str:
    """Description tiếng Việt từ EventCandidate; fallback theo event_type."""
    provided = payload.get("description")
    if provided:
        return provided
    labels = {
        "xam_nhap": "Phát hiện xâm nhập khu vực hạn chế",
        "dam_dong": "Phát hiện tụ tập đông người",
        "vat_the_bo_quen": "Phát hiện vật thể bỏ quên",
        "te_nga": "Nghi ngờ té ngã",
    }
    label = labels.get(event_type, "Sự kiện an ninh")
    level = "CRITICAL" if severity == "critical" else "CẢNH BÁO"
    return f"{level}: {label} tại Camera #{camera_id}"
