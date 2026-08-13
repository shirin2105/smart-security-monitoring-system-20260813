import json
import logging
import math
import os
import time
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, or_, update

from app.db.database import SessionLocal
from app.db.models import AssessmentJob, IncidentAssessment
from app.services import assessment_provider as provider
from app.services.assessment_policy import fallback_assessment, validate_assessment

MAX_ATTEMPTS = 2
logger = logging.getLogger("assessment-worker")


def settings():
    timeout = float(os.getenv("ASSESSMENT_LLM_TIMEOUT_SECONDS", "15"))
    lease = int(os.getenv("ASSESSMENT_LEASE_SECONDS", "60"))
    poll = float(os.getenv("ASSESSMENT_POLL_SECONDS", "2"))
    response_bytes = int(os.getenv("ASSESSMENT_MAX_RESPONSE_BYTES", "65536"))
    if not math.isfinite(timeout) or not math.isfinite(poll) or timeout <= 0 or poll <= 0:
        raise ValueError("assessment timeout and poll interval must be positive finite values")
    if lease <= timeout * MAX_ATTEMPTS + 5:
        raise ValueError("assessment lease must exceed two provider timeouts plus 5 seconds")
    if not 1024 <= response_bytes <= 1048576:
        raise ValueError("assessment response byte limit must be between 1024 and 1048576")
    return timeout, lease, poll


def claim_job(db, now=None, incident_id=None):
    now = now or datetime.now(UTC)
    if db.bind.dialect.name == "sqlite" and now.tzinfo is not None:
        now = now.replace(tzinfo=None)
    eligible = or_(
        and_(AssessmentJob.status == "READY", AssessmentJob.available_at <= now),
        and_(AssessmentJob.status == "PROCESSING", AssessmentJob.lease_expires_at < now),
    )
    query = db.query(AssessmentJob).filter(eligible)
    if incident_id is not None:
        query = query.filter(AssessmentJob.incident_id == incident_id)
    is_postgres = db.bind.dialect.name == "postgresql"
    if is_postgres:
        query = query.with_for_update(skip_locked=True)
    job = query.order_by(AssessmentJob.id).first()
    if not job:
        db.rollback()
        return None
    token = uuid.uuid4().hex
    _, lease_seconds, _ = settings()
    lease_expires_at = now + timedelta(seconds=lease_seconds)
    if not is_postgres:
        changed = db.execute(update(AssessmentJob).where(
            AssessmentJob.id == job.id, eligible,
        ).values(status="PROCESSING", lease_token=token, lease_expires_at=lease_expires_at)).rowcount
        db.commit()
        return (job.id, token) if changed == 1 else None
    job.status, job.lease_token, job.lease_expires_at = "PROCESSING", token, lease_expires_at
    db.commit()
    return job.id, token


def reserve_attempt(job_id, token):
    db = SessionLocal()
    try:
        now = datetime.now(UTC)
        if db.bind.dialect.name == "sqlite" and now.tzinfo is not None:
            now = now.replace(tzinfo=None)
        changed = db.execute(update(AssessmentJob).where(
            AssessmentJob.id == job_id,
            AssessmentJob.lease_token == token,
            AssessmentJob.status == "PROCESSING",
            AssessmentJob.lease_expires_at >= now,
            AssessmentJob.provider_attempts < MAX_ATTEMPTS,
        ).values(provider_attempts=AssessmentJob.provider_attempts + 1)).rowcount
        db.commit()
        return changed == 1
    finally:
        db.close()


def _finish(job_id, token, result, is_fallback, error=None):
    db = SessionLocal()
    try:
        now = datetime.now(UTC)
        if db.bind.dialect.name == "sqlite" and now.tzinfo is not None:
            now = now.replace(tzinfo=None)
        incident_id = db.query(AssessmentJob.incident_id).filter(AssessmentJob.id == job_id).scalar()
        changed = db.execute(update(AssessmentJob).where(
            AssessmentJob.id == job_id,
            AssessmentJob.lease_token == token,
            AssessmentJob.status == "PROCESSING",
            AssessmentJob.lease_expires_at >= now,
        ).values(status="COMPLETED", lease_token=None, lease_expires_at=None,
                 last_error=(error or "")[:255] or None)).rowcount
        if changed != 1:
            db.rollback()
            return False
        if db.query(IncidentAssessment).filter_by(incident_id=incident_id, version=1).first() is None:
            db.add(IncidentAssessment(incident_id=incident_id, version=1,
                provider="fallback" if is_fallback else "llm", is_fallback=int(is_fallback), **result))
        db.commit()
        return True
    finally:
        db.close()


def process_claim(job_id, token, provider_fn=provider.assess):
    db = SessionLocal()
    try:
        job = db.query(AssessmentJob).filter_by(id=job_id, lease_token=token, status="PROCESSING").first()
        if not job:
            return False
        snapshot = json.loads(job.snapshot_json)
    finally:
        db.close()
    reason = "provider attempt budget exhausted"
    while reserve_attempt(job_id, token):
        try:
            return _finish(job_id, token, validate_assessment(provider_fn(snapshot)), False)
        except provider.TransientProviderError:
            reason = "transient provider failure"
            continue
        except (provider.PermanentProviderError, ValueError):
            reason = "invalid or permanent provider failure"
            break
        except Exception:
            reason = "unexpected provider failure"
            break
    return _finish(job_id, token, fallback_assessment(reason), True, reason)


def run_once():
    db = SessionLocal()
    try:
        claim = claim_job(db)
    finally:
        db.close()
    if not claim:
        return False
    try:
        return process_claim(*claim)
    except Exception:
        try:
            _finish(*claim, fallback_assessment("worker processing failure"), True, "worker processing failure")
        except Exception:
            pass
        return True


def main():
    _, _, poll = settings()
    while True:
        try:
            worked = run_once()
        except Exception:
            logger.warning("assessment worker database iteration failed; retrying")
            worked = False
        if not worked:
            time.sleep(poll)


if __name__ == "__main__":
    main()
