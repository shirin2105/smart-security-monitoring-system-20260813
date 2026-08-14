from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Incident, AuditLog, User
from app.api.auth import get_current_user
from app.services.simulator import create_simulated_incident
from app.services.websocket import manager

router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts & Incidents"])

import json

class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: int
    camera_name: str
    event_type: str
    severity: str
    description: str
    status: str
    source: str = "SIMULATOR"
    created_at: datetime
    bbox: Optional[List[float]] = None

class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_name: str
    action: str
    incident_id: Optional[int]
    timestamp: datetime

@router.get("", response_model=List[IncidentResponse])
def get_incidents(db: Session = Depends(get_db)):
    incidents = db.query(Incident).order_by(Incident.created_at.desc()).limit(50).all()
    results = []
    for inc in incidents:
        bbox = json.loads(inc.bbox_json) if inc.bbox_json else None
        results.append({
            "id": inc.id,
            "camera_id": inc.camera_id,
            "camera_name": inc.camera.name if inc.camera else f"Camera #{inc.camera_id}",
            "event_type": inc.event_type,
            "severity": inc.severity,
            "description": inc.description,
            "status": inc.status,
            "source": inc.source,
            "created_at": inc.created_at,
            "bbox": bbox,
        })
    return results

@router.post("/{incident_id}/acknowledge")
async def acknowledge_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Không tìm thấy sự cố")
    
    incident.status = "acknowledged"
    
    audit = AuditLog(
        user_id=current_user.id,
        incident_id=incident.id,
        action=f"Bảo vệ {current_user.full_name} đã XÁC NHẬN xử lý sự cố #{incident.id}",
        timestamp=datetime.now(timezone.utc)
    )
    db.add(audit)
    db.commit()

    # Broadcast update
    await manager.broadcast({
        "type": "ALERT_UPDATED",
        "incident_id": incident.id,
        "status": "acknowledged",
        "action_by": current_user.full_name
    })

    return {"message": "Đã xác nhận xử lý sự cố", "incident_id": incident.id, "status": "acknowledged"}

@router.post("/{incident_id}/escalate")
async def escalate_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Không tìm thấy sự cố")
    
    incident.status = "escalated"
    
    audit = AuditLog(
        user_id=current_user.id,
        incident_id=incident.id,
        action=f"Bảo vệ {current_user.full_name} đã CHUYỂN QUẢN LÝ xử lý sự cố #{incident.id}",
        timestamp=datetime.now(timezone.utc)
    )
    db.add(audit)
    db.commit()

    # Broadcast update
    await manager.broadcast({
        "type": "ALERT_UPDATED",
        "incident_id": incident.id,
        "status": "escalated",
        "action_by": current_user.full_name
    })

    return {"message": "Đã chuyển quản lý sự cố", "incident_id": incident.id, "status": "escalated"}

@router.post("/simulate")
async def trigger_simulation():
    incident = await create_simulated_incident()
    return {"message": "Simulated incident triggered", "incident": incident}

@router.get("/audit-logs", response_model=List[AuditLogResponse])
def get_audit_logs(db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100).all()
    results = []
    for log in logs:
        results.append({
            "id": log.id,
            "user_name": log.user.full_name if log.user else "Hệ Thống",
            "action": log.action,
            "incident_id": log.incident_id,
            "timestamp": log.timestamp
        })
    return results
