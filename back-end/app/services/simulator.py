import asyncio
import random
import logging
from datetime import datetime, timezone
from app.db.database import SessionLocal
from app.db.models import Incident, Camera
from app.services.websocket import manager

logger = logging.getLogger("uvicorn.error")

SIMULATION_EVENTS = [
    {
        "camera_id": 3,
        "event_type": "xam_nhap",
        "severity": "critical",
        "description": "CẢNH BÁO CRITICAL: Phát hiện vượt hàng rào phía Tây!",
        "bbox": [120, 80, 240, 260]
    },
    {
        "camera_id": 6,
        "event_type": "dam_dong",
        "severity": "warning",
        "description": "CẢNH BÁO WARNING: Tụ tập đông người (>5 người) tại Hành Lang T4",
        "bbox": [200, 150, 450, 320]
    },
    {
        "camera_id": 1,
        "event_type": "xam_nhap",
        "severity": "warning",
        "description": "CẢNH BÁO WARNING: Di chuyển ngoài giờ quy định khu vực Cổng Chính",
        "bbox": [300, 100, 420, 280]
    },
    {
        "camera_id": 4,
        "event_type": "xam_nhap",
        "severity": "critical",
        "description": "CẢNH BÁO CRITICAL: Mở cửa bất hợp pháp Phòng Server Tầng Hầm",
        "bbox": [150, 120, 310, 300]
    }
]

async def create_simulated_incident(event_data: dict = None):
    db = SessionLocal()
    try:
        if not event_data:
            event_data = random.choice(SIMULATION_EVENTS)

        camera = db.query(Camera).filter(Camera.id == event_data["camera_id"]).first()
        camera_name = camera.name if camera else f"Camera #{event_data['camera_id']}"

        incident = Incident(
            camera_id=event_data["camera_id"],
            event_type=event_data["event_type"],
            severity=event_data["severity"],
            description=event_data["description"],
            status="pending",
            source="SIMULATOR",
            created_at=datetime.now(timezone.utc)
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
                "created_at": incident.created_at.isoformat(),
                "bbox": event_data.get("bbox", [100, 100, 200, 200])
            }
        }

        await manager.broadcast(alert_payload)
        logger.info(f"Simulated incident #{incident.id} created and broadcasted: {incident.description}")
        return alert_payload["incident"]

    except Exception as e:
        logger.error(f"Failed to create simulated incident: {e}")
        db.rollback()
        return None
    finally:
        db.close()

async def background_event_simulator(interval_seconds: int = 25):
    logger.info(f"Background camera event simulator started (Interval: {interval_seconds}s)")
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            await create_simulated_incident()
        except asyncio.CancelledError:
            logger.info("Background camera event simulator cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in background simulator loop: {e}")
