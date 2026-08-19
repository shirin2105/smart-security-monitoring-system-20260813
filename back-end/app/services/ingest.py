"""Persist authenticated CV candidates with durable duplicate suppression."""

import hashlib
import json
from datetime import UTC, datetime

from app.db.database import SessionLocal
from app.db.models import AssessmentJob, Camera, Incident
from app.services.websocket import manager
from sqlalchemy.exc import IntegrityError

EVENT_TYPE_MAP = {
    "ZONE_INTRUSION": "xam_nhap",
    "CROWD_THRESHOLD": "dam_dong",
    "ABANDONED_OBJECT": "vat_the_bo_quen",
    "SUSPECTED_FALL": "te_nga",
    "COVERAGE_DEGRADED": "suy_giam_vung_phu",
}
EVENT_SEVERITY_MAP = {
    "ZONE_INTRUSION": "critical",
    "CROWD_THRESHOLD": "high",
    "ABANDONED_OBJECT": "warning",
    "SUSPECTED_FALL": "critical",
    "COVERAGE_DEGRADED": "warning",
}
CAMERA_ID_MAP = {
    "cam_01": 1, "cam_02": 2, "cam_03": 3,
    "cam_04": 4, "cam_05": 5, "cam_06": 6,
}


class IdempotencyConflict(ValueError):
    pass


class CandidateReferenceError(ValueError):
    pass


def map_event_type(event_type: str) -> str:
    try:
        return EVENT_TYPE_MAP[event_type]
    except KeyError as exc:
        raise CandidateReferenceError(f"Unsupported event type: {event_type}") from exc


def map_camera_id(camera_id: str, db) -> int:
    if camera_id in CAMERA_ID_MAP:
        mapped_id = CAMERA_ID_MAP[camera_id]
    elif camera_id.startswith("cam_"):
        try:
            mapped_id = int(camera_id.split("_")[1])
        except (IndexError, ValueError):
            raise CandidateReferenceError(f"Unknown camera: {camera_id}")
    else:
        raise CandidateReferenceError(f"Unknown camera: {camera_id}")
    if db.query(Camera).filter(Camera.id == mapped_id).first() is None:
        raise CandidateReferenceError(f"Unknown camera: {camera_id}")
    return mapped_id


def _payload_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def assessment_snapshot(payload: dict, camera_id: int) -> dict:
    """Return only policy-approved, non-identifying event metadata."""
    observations = payload.get("observations") or {}
    return {
        "cameraId": camera_id,
        "zoneId": payload.get("zoneId"),
        "eventType": payload.get("eventType"),
        "detectedAt": str(payload.get("detectedAt")),
        "firstSeenAt": str(payload.get("firstSeenAt")),
        "lastSeenAt": str(payload.get("lastSeenAt")),
        "confidence": float(payload.get("confidence", 0.0)),
        "trackCount": int(payload.get("trackCount", 1)),
        "observations": {
            key: observations.get(key)
            for key in ("personCount", "dwellSeconds", "insideZone", "stationarySeconds", "ownerAbsentSeconds")
        },
        "modelVersion": str(payload.get("modelVersion", "deimv2-phase7a")),
        "ruleVersion": str(payload.get("ruleVersion", "intrusion-rule-v1")),
        "policyVersion": int(payload.get("policyVersion", 1)),
    }


def _incident_payload(incident: Incident, camera_name: str) -> dict:
    bbox = json.loads(incident.bbox_json) if incident.bbox_json else None
    return {
        "id": incident.id,
        "camera_id": incident.camera_id,
        "camera_name": camera_name,
        "event_type": incident.event_type,
        "severity": incident.severity,
        "description": incident.description,
        "status": incident.status,
        "source": incident.source,
        "created_at": incident.created_at.isoformat(),
        "bbox": bbox,
    }


async def ingest_event_candidate(payload: dict) -> dict:
    db = SessionLocal()
    candidate_id = payload["candidateId"]
    digest = _payload_hash(payload)
    try:
        existing = db.query(Incident).filter(Incident.candidate_id == candidate_id).first()
        if existing:
            if existing.payload_hash == digest:
                return _duplicate_result(existing, digest, db)
            if payload.get("eventState") in ("UPDATE", "END"):
                bbox_data = payload.get("bbox")
                if bbox_data is not None:
                    existing.bbox_json = json.dumps(bbox_data)
                existing.payload_hash = digest
                db.commit()
                db.refresh(existing)
                camera = db.query(Camera).filter(Camera.id == existing.camera_id).first()
                incident_payload = _incident_payload(existing, camera.name if camera else f"Camera #{existing.camera_id}")
                incident_payload["bbox"] = bbox_data
                await manager.broadcast({"type": "UPDATE_ALERT", "incident": incident_payload})
                return {"status": "ACCEPTED", "incident": incident_payload}
            return _duplicate_result(existing, digest, db)

        camera_id = map_camera_id(payload.get("cameraId", ""), db)
        canonical_event_type = payload["eventType"]
        event_type = map_event_type(canonical_event_type)
        severity = EVENT_SEVERITY_MAP[canonical_event_type]
        bbox_data = payload.get("bbox")
        bbox_json_str = json.dumps(bbox_data) if bbox_data else None
        incident = Incident(
            camera_id=camera_id,
            event_type=event_type,
            severity=severity,
            description=_build_description(payload, camera_id, event_type, severity),
            status="pending",
            source="CV",
            candidate_id=candidate_id,
            payload_hash=digest,
            bbox_json=bbox_json_str,
            artifact_url=(payload.get("artifact") or {}).get("uri"),
            redaction_status=(payload.get("artifact") or {}).get("redactionStatus", "COMPLETE"),
            created_at=datetime.now(UTC),
        )
        db.add(incident)
        db.flush()
        db.add(AssessmentJob(
            incident_id=incident.id,
            status="READY",
            snapshot_json=json.dumps(assessment_snapshot(payload, camera_id), separators=(",", ":")),
            available_at=datetime.now(UTC),
        ))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = db.query(Incident).filter(Incident.candidate_id == candidate_id).first()
            if existing:
                return _duplicate_result(existing, digest, db)
            raise
        db.refresh(incident)
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        incident_payload = _incident_payload(incident, camera.name if camera else f"Camera #{camera_id}")
        incident_payload["bbox"] = bbox_data
        await manager.broadcast({"type": "NEW_ALERT", "incident": incident_payload})
        return {"status": "ACCEPTED", "incident": incident_payload}
    finally:
        db.close()


def _duplicate_result(existing: Incident, digest: str, db) -> dict:
    if existing.payload_hash != digest:
        raise IdempotencyConflict("Candidate identifier was already used with a different payload")
    camera = db.query(Camera).filter(Camera.id == existing.camera_id).first()
    return {
        "status": "DUPLICATE_IGNORED",
        "incident": _incident_payload(existing, camera.name if camera else f"Camera #{existing.camera_id}"),
    }


def _build_description(payload: dict, camera_id: int, event_type: str, severity: str) -> str:
    labels = {
        "xam_nhap": "Phát hiện xâm nhập khu vực hạn chế",
        "dam_dong": "Phát hiện tụ tập đông người",
        "vat_the_bo_quen": "Phát hiện vật thể bỏ quên",
        "te_nga": "Nghi ngờ té ngã",
        "suy_giam_vung_phu": "Phát hiện suy giảm vùng phủ camera",
    }
    observations = payload["observations"]
    detail = ""
    if payload["eventType"] == "CROWD_THRESHOLD":
        detail = f" ({observations['personCount']} người)"
    elif payload["eventType"] == "ABANDONED_OBJECT" and observations.get("stationarySeconds") is not None:
        detail = f" ({observations['stationarySeconds']} giây)"
    level = "CRITICAL" if severity == "critical" else "CẢNH BÁO"
    return f"{level}: {labels[event_type]}{detail} tại Camera #{camera_id}"


async def mark_incident_artifact_ready(incident_id: int, uri: str, redaction_status: str) -> dict | None:
    """Attach a rendered evidence clip to an already-posted incident and notify listeners."""
    db = SessionLocal()
    try:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if incident is None:
            return None
        incident.artifact_url = uri
        incident.redaction_status = redaction_status
        db.commit()
        db.refresh(incident)
        camera = db.query(Camera).filter(Camera.id == incident.camera_id).first()
        incident_payload = _incident_payload(incident, camera.name if camera else f"Camera #{incident.camera_id}")
        await manager.broadcast({"type": "ALERT_UPDATED", "incident_id": incident.id})
        return incident_payload
    finally:
        db.close()

