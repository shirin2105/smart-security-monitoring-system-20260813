import json
import asyncio
from datetime import UTC, datetime, timedelta

from app.db.database import SessionLocal
from app.db.models import AssessmentJob, Incident, IncidentAssessment
from app.services.assessment_provider import PermanentProviderError, TransientProviderError
from app.services.assessment_worker import _finish, claim_job, process_claim, reserve_attempt, settings
from app.services import ingest
from sqlalchemy import update
from test_api import INGEST_HEADERS, candidate_payload, client


def _ingest(candidate_id):
    return client.post("/api/v1/events/ingest", headers=INGEST_HEADERS, json=candidate_payload(candidate_id))


def test_ingest_enqueues_one_allowlisted_metadata_snapshot():
    payload = candidate_payload("evt-assessment-allowlist")
    payload["artifact"] = {"available": True, "contentType": "image/jpeg", "redactionStatus": "COMPLETE", "uri": "secret"}
    payload["trackIds"] = [123, 456]
    first = client.post("/api/v1/events/ingest", headers=INGEST_HEADERS, json=payload)
    duplicate = client.post("/api/v1/events/ingest", headers=INGEST_HEADERS, json=payload)
    db = SessionLocal()
    try:
        incident_id = first.json()["incident"]["id"]
        jobs = db.query(AssessmentJob).filter_by(incident_id=incident_id).all()
        snapshot = json.loads(jobs[0].snapshot_json)
        assert duplicate.status_code == 200
        assert len(jobs) == 1
        assert "artifact" not in snapshot and "trackIds" not in snapshot
        assert set(snapshot) == {"cameraId", "zoneId", "eventType", "detectedAt", "firstSeenAt",
            "lastSeenAt", "confidence", "trackCount", "observations", "modelVersion", "ruleVersion", "policyVersion"}
    finally:
        db.close()


def test_job_insert_failure_rolls_back_incident(monkeypatch):
    payload = candidate_payload("evt-assessment-rollback")
    real_factory = ingest.SessionLocal
    db = real_factory()
    original_add = db.add
    def reject_job(value):
        if isinstance(value, AssessmentJob):
            raise RuntimeError("job insert failed")
        original_add(value)
    monkeypatch.setattr(db, "add", reject_job)
    monkeypatch.setattr(ingest, "SessionLocal", lambda: db)
    try:
        try:
            asyncio.run(ingest.ingest_event_candidate(payload))
        except RuntimeError:
            pass
        else:
            raise AssertionError("expected job insert failure")
    finally:
        monkeypatch.setattr(ingest, "SessionLocal", real_factory)
    check = real_factory()
    try:
        assert check.query(Incident).filter_by(candidate_id=payload["candidateId"]).count() == 0
    finally:
        check.close()


def test_claim_reclaim_and_stale_fencing():
    response = _ingest("evt-assessment-fence")
    incident_id = response.json()["incident"]["id"]
    db = SessionLocal()
    try:
        first = claim_job(db, incident_id=incident_id)
        job = db.query(AssessmentJob).filter_by(incident_id=incident_id).one()
        job.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
        second = claim_job(db, incident_id=incident_id)
    finally:
        db.close()
    valid = {"outcome": "MONITOR", "summary": "ok", "rationale": "metadata"}
    assert first[0] == second[0] and first[1] != second[1]
    assert process_claim(*first, provider_fn=lambda _: valid) is False
    assert process_claim(*second, provider_fn=lambda _: valid) is True


def test_worker_success_does_not_mutate_incident_and_writes_one_version():
    response = _ingest("evt-assessment-success")
    incident_id = response.json()["incident"]["id"]
    db = SessionLocal()
    try:
        before = db.query(Incident).get(incident_id)
        original = (before.severity, before.status)
        claim = claim_job(db, incident_id=incident_id)
    finally:
        db.close()
    assert process_claim(*claim, provider_fn=lambda _: {"outcome": "URGENT_REVIEW", "summary": "review", "rationale": "signal"})
    db = SessionLocal()
    try:
        after = db.query(Incident).get(incident_id)
        assert (after.severity, after.status) == original
        assert db.query(IncidentAssessment).filter_by(incident_id=incident_id, version=1).count() == 1
    finally:
        db.close()


def test_worker_retries_transient_twice_then_falls_back():
    response = _ingest("evt-assessment-retry")
    incident_id = response.json()["incident"]["id"]
    calls = []
    def unavailable(_):
        calls.append(1)
        raise TransientProviderError("timeout")
    db = SessionLocal()
    try:
        claim = claim_job(db, incident_id=incident_id)
    finally:
        db.close()
    assert process_claim(*claim, provider_fn=unavailable)
    db = SessionLocal()
    try:
        assessment = db.query(IncidentAssessment).filter_by(incident_id=incident_id).one()
        job = db.query(AssessmentJob).filter_by(incident_id=incident_id).one()
        assert len(calls) == 2 and assessment.is_fallback == 1 and job.provider_attempts == 2
    finally:
        db.close()


def test_worker_missing_key_falls_back_without_retry():
    response = _ingest("evt-assessment-no-key")
    incident_id = response.json()["incident"]["id"]
    db = SessionLocal()
    try:
        claim = claim_job(db, incident_id=incident_id)
    finally:
        db.close()
    assert process_claim(*claim, provider_fn=lambda _: (_ for _ in ()).throw(PermanentProviderError("missing API key")))
    db = SessionLocal()
    try:
        job = db.query(AssessmentJob).filter_by(incident_id=incident_id).one()
        assert job.provider_attempts == 1
    finally:
        db.close()


def test_attempt_budget_is_durable_across_reclaim():
    incident_id = _ingest("evt-assessment-budget").json()["incident"]["id"]
    db = SessionLocal()
    try:
        first = claim_job(db, incident_id=incident_id)
        assert reserve_attempt(*first)
        job = db.query(AssessmentJob).filter_by(incident_id=incident_id).one()
        job.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
        second = claim_job(db, incident_id=incident_id)
    finally:
        db.close()
    calls = []
    def transient(_):
        calls.append(1)
        raise TransientProviderError("secret timeout")
    assert process_claim(*second, provider_fn=transient)
    db = SessionLocal()
    try:
        job = db.query(AssessmentJob).filter_by(incident_id=incident_id).one()
        assert len(calls) == 1 and job.provider_attempts == 2
        assert "secret" not in (job.last_error or "")
    finally:
        db.close()


def test_invalid_non_object_output_falls_back():
    incident_id = _ingest("evt-assessment-list").json()["incident"]["id"]
    db = SessionLocal()
    try:
        claim = claim_job(db, incident_id=incident_id)
    finally:
        db.close()
    assert process_claim(*claim, provider_fn=lambda _: [])
    db = SessionLocal()
    try:
        assert db.query(IncidentAssessment).filter_by(incident_id=incident_id).one().is_fallback == 1
    finally:
        db.close()


def test_invalid_lease_configuration_is_rejected(monkeypatch):
    monkeypatch.setenv("ASSESSMENT_LLM_TIMEOUT_SECONDS", "15")
    monkeypatch.setenv("ASSESSMENT_LEASE_SECONDS", "35")
    try:
        settings()
    except ValueError:
        pass
    else:
        raise AssertionError("unsafe lease accepted")


def test_expired_lease_cannot_finish_before_reclaim():
    incident_id = _ingest("evt-assessment-expired-finish").json()["incident"]["id"]
    db = SessionLocal()
    try:
        claim = claim_job(db, incident_id=incident_id)
        job = db.query(AssessmentJob).filter_by(incident_id=incident_id).one()
        job.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    finally:
        db.close()
    result = {"outcome": "MONITOR", "summary": "ok", "rationale": "metadata"}
    assert _finish(*claim, result, False) is False
    db = SessionLocal()
    try:
        assert db.query(IncidentAssessment).filter_by(incident_id=incident_id).count() == 0
    finally:
        db.close()


def test_sqlite_concurrent_claim_has_single_token_winner():
    incident_id = _ingest("evt-assessment-concurrent-claim").json()["incident"]["id"]
    contender = SessionLocal()
    winner = SessionLocal()
    try:
        stale_id = contender.query(AssessmentJob.id).filter_by(incident_id=incident_id).scalar()
        contender.rollback()
        claim = claim_job(winner, incident_id=incident_id)
        overwritten = contender.execute(update(AssessmentJob).where(
            AssessmentJob.id == stale_id,
            AssessmentJob.status == "READY",
        ).values(status="PROCESSING", lease_token="challenger")).rowcount
        contender.commit()
        contender.expire_all()
        job = contender.query(AssessmentJob).filter_by(incident_id=incident_id).one()
        assert overwritten == 0 and job.lease_token == claim[1]
    finally:
        contender.close()
        winner.close()


def test_non_finite_worker_float_configuration_is_rejected(monkeypatch):
    for name, value in (("ASSESSMENT_LLM_TIMEOUT_SECONDS", "nan"),
                        ("ASSESSMENT_LLM_TIMEOUT_SECONDS", "inf"),
                        ("ASSESSMENT_POLL_SECONDS", "nan"),
                        ("ASSESSMENT_POLL_SECONDS", "-inf")):
        monkeypatch.setenv("ASSESSMENT_LLM_TIMEOUT_SECONDS", "15")
        monkeypatch.setenv("ASSESSMENT_POLL_SECONDS", "2")
        monkeypatch.setenv(name, value)
        try:
            settings()
        except ValueError:
            pass
        else:
            raise AssertionError(f"non-finite {name} accepted")
