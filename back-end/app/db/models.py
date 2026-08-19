from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def utc_now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="bao_ve")  # "bao_ve", "quan_ly"
    full_name = Column(String(100), nullable=False)

    audit_logs = relationship("AuditLog", back_populates="user")

class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    location = Column(String(150), nullable=False)
    stream_url = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="online")  # "online", "warning", "offline"
    source = Column(String(20), nullable=False, default="SIMULATOR")  # "CV", "SIMULATOR"
    ai_enabled = Column(Boolean, nullable=False, default=True)  # AI assessment on/off per camera

    incidents = relationship("Incident", back_populates="camera")

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    event_type = Column(String(50), nullable=False)  # "xam_nhap", "dam_dong"
    severity = Column(String(20), nullable=False, default="warning")  # "warning", "critical"
    description = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # "pending", "acknowledged", "escalated"
    source = Column(String(20), nullable=False, default="SIMULATOR")  # "CV", "SIMULATOR"
    candidate_id = Column(String(255), nullable=True, unique=True, index=True)
    payload_hash = Column(String(64), nullable=True)
    bbox_json = Column(Text, nullable=True)
    artifact_url = Column(String(255), nullable=True)
    redaction_status = Column(String(20), nullable=True, default="COMPLETE")
    created_at = Column(DateTime, default=utc_now, nullable=False)

    camera = relationship("Camera", back_populates="incidents")
    audit_logs = relationship("AuditLog", back_populates="incident")
    assessment_jobs = relationship("AssessmentJob", back_populates="incident")
    assessments = relationship("IncidentAssessment", back_populates="incident")

class AssessmentJob(Base):
    __tablename__ = "assessment_jobs"
    __table_args__ = (UniqueConstraint("incident_id", name="uq_assessment_jobs_incident"),)

    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="READY", index=True)
    snapshot_json = Column(Text, nullable=False)
    provider_attempts = Column(Integer, nullable=False, default=0)
    lease_token = Column(String(64), nullable=True)
    lease_expires_at = Column(DateTime, nullable=True)
    available_at = Column(DateTime, nullable=False, default=utc_now)
    last_error = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    incident = relationship("Incident", back_populates="assessment_jobs")

class IncidentAssessment(Base):
    __tablename__ = "incident_assessments"
    __table_args__ = (UniqueConstraint("incident_id", "version", name="uq_incident_assessment_version"),)

    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    outcome = Column(String(30), nullable=False)
    summary = Column(Text, nullable=False)
    rationale = Column(Text, nullable=False)
    provider = Column(String(50), nullable=False)
    is_fallback = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    incident = relationship("Incident", back_populates="assessments")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=True)
    action = Column(String(255), nullable=False)
    timestamp = Column(DateTime, default=utc_now, nullable=False)

    user = relationship("User", back_populates="audit_logs")
    incident = relationship("Incident", back_populates="audit_logs")
