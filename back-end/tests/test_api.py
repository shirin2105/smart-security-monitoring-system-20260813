import json
import math
import os

TEST_DB_PATH = "./test_security_monitoring.db"
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["EVENT_INGEST_TOKEN"] = "test-producer-token"

from app.db.database import init_db_and_seed
from fastapi.testclient import TestClient

from app.main import app

# Ensure tables and seed data are created for SQLite test database
init_db_and_seed()

client = TestClient(app)
INGEST_HEADERS = {"Authorization": "Bearer test-producer-token"}


def candidate_payload(candidate_id: str, camera_id: str = "cam_01", event_type: str = "ZONE_INTRUSION"):
    timestamp = "2026-08-11T08:00:00Z"
    return {
        "candidateId": candidate_id,
        "sourceEngine": "CV",
        "cameraId": camera_id,
        "zoneId": "restricted_gate",
        "sourceType": "SIMULATED",
        "eventType": event_type,
        "eventDetected": True,
        "detectedAt": timestamp,
        "firstSeenAt": timestamp,
        "lastSeenAt": timestamp,
        "confidence": 0.9,
        "trackCount": 1,
        "trackIds": [1],
        "observations": {"personCount": 1, "insideZone": True},
        "modelVersion": "deimv2-phase7a",
        "ruleVersion": "intrusion-rule-v1",
        "policyVersion": 1,
        "artifact": {"available": False, "redactionStatus": "PENDING"},
    }

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_login():
    response = client.post("/api/v1/auth/login", json={"username": "guard", "password": "guard123"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["username"] == "guard"
    assert data["user"]["role"] == "bao_ve"

def test_get_cameras():
    response = client.get("/api/v1/cameras")
    assert response.status_code == 200
    cameras = response.json()
    assert len(cameras) == 6
    assert cameras[0]["name"] == "Camera Cổng Chính"

def test_alerts_and_acknowledge():
    # Tạo incident qua ingest (không còn seed incident mẫu)
    res_ingest = client.post(
        "/api/v1/events/ingest", headers=INGEST_HEADERS, json=candidate_payload("evt-ack-001")
    )
    assert res_ingest.status_code == 201
    first_incident_id = res_ingest.json()["incident"]["id"]

    # Login as guard to get token
    res_login = client.post("/api/v1/auth/login", json={"username": "guard", "password": "guard123"})
    token = res_login.json()["access_token"]

    # Acknowledge
    res_ack = client.post(
        f"/api/v1/alerts/{first_incident_id}/acknowledge",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_ack.status_code == 200
    assert res_ack.json()["status"] == "acknowledged"

    # Check audit log
    res_audit = client.get("/api/v1/alerts/audit-logs")
    assert res_audit.status_code == 200
    logs = res_audit.json()
    assert len(logs) > 0


def test_ingest_event_candidate():
    """CV pipeline EventCandidate -> Incident persisted + readable qua alerts."""
    payload = candidate_payload("evt-test-001")
    response = client.post("/api/v1/events/ingest", headers={**INGEST_HEADERS, "Idempotency-Key": payload["candidateId"]}, json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "ACCEPTED"
    assert data["incident"]["event_type"] == "xam_nhap"
    assert data["incident"]["severity"] == "critical"
    assert data["incident"]["camera_id"] == 1

    # Incident phải đọc lại được qua alerts
    res_alerts = client.get("/api/v1/alerts")
    ids = [inc["id"] for inc in res_alerts.json()]
    assert data["incident"]["id"] in ids


def test_ingest_event_candidate_type_mapping():
    """CROWD_THRESHOLD -> dam_dong, cam_02 -> camera 2, HIGH -> high."""
    payload = candidate_payload("evt-crowd-001", camera_id="cam_02", event_type="CROWD_THRESHOLD")
    response = client.post("/api/v1/events/ingest", headers={**INGEST_HEADERS, "Idempotency-Key": payload["candidateId"]}, json=payload)
    assert response.status_code == 201
    incident = response.json()["incident"]
    assert incident["event_type"] == "dam_dong"
    assert incident["severity"] == "high"
    assert incident["camera_id"] == 2


def test_ingest_persists_detected_at_and_artifact():
    """Live-CV alert carries video-timeline detectedAt + cut evidence clip URL."""
    payload = candidate_payload("evt-evidence-001", event_type="ABANDONED_OBJECT")
    payload["detectedAt"] = "2026-01-01T00:00:13.750Z"
    payload["firstSeenAt"] = "2026-01-01T00:00:13.750Z"
    payload["lastSeenAt"] = "2026-01-01T00:00:13.750Z"
    payload["artifact"] = {
        "available": True,
        "contentType": "video/mp4",
        "redactionStatus": "COMPLETE",
        "uri": "/evidence/evt-evidence-001.mp4",
    }
    response = client.post(
        "/api/v1/events/ingest",
        headers={**INGEST_HEADERS, "Idempotency-Key": payload["candidateId"]},
        json=payload,
    )
    assert response.status_code == 201
    incident = response.json()["incident"]
    assert incident["detected_at"].startswith("2026-01-01T00:00:13.75")
    assert incident["artifact_url"] == "/evidence/evt-evidence-001.mp4"
    assert incident["redaction_status"] == "COMPLETE"

    # Re-read via REST list — fields must round-trip to the frontend.
    alerts = {inc["id"]: inc for inc in client.get("/api/v1/alerts").json()}
    persisted = alerts[incident["id"]]
    assert persisted["detected_at"].startswith("2026-01-01T00:00:13.75")
    assert persisted["artifact_url"] == "/evidence/evt-evidence-001.mp4"
    assert persisted["redaction_status"] == "COMPLETE"



def test_ingest_requires_matching_bearer_token():
    payload = candidate_payload("evt-auth")
    assert client.post("/api/v1/events/ingest", json=payload).status_code == 401
    assert client.post(
        "/api/v1/events/ingest",
        headers={"Authorization": "Bearer wrong"},
        json=payload,
    ).status_code == 401


def test_ingest_rejects_empty_configured_token_and_malformed_bearer(monkeypatch):
    payload = candidate_payload("evt-auth-edge")
    monkeypatch.setenv("EVENT_INGEST_TOKEN", "")
    assert client.post(
        "/api/v1/events/ingest",
        headers={"Authorization": "Bearer test-producer-token"},
        json=payload,
    ).status_code == 401
    monkeypatch.setenv("EVENT_INGEST_TOKEN", "test-producer-token")
    assert client.post(
        "/api/v1/events/ingest",
        headers={"Authorization": "Basic test-producer-token"},
        json=payload,
    ).status_code == 401


def test_ingest_rejects_mismatched_idempotency_key_and_extra_fields():
    payload = candidate_payload("evt-contract")
    mismatch = client.post(
        "/api/v1/events/ingest",
        headers={**INGEST_HEADERS, "Idempotency-Key": "different"},
        json=payload,
    )
    extra = client.post(
        "/api/v1/events/ingest",
        headers=INGEST_HEADERS,
        json={**payload, "rawImage": [[0, 1]]},
    )
    nested_extra = client.post(
        "/api/v1/events/ingest",
        headers=INGEST_HEADERS,
        json={**payload, "observations": {"personCount": 1, "unknown": True}},
    )

    assert mismatch.status_code == 409
    assert extra.status_code == 422
    assert nested_extra.status_code == 422


def test_ingest_duplicate_is_suppressed_and_changed_payload_conflicts():
    payload = candidate_payload("evt-idempotent")
    headers = {**INGEST_HEADERS, "Idempotency-Key": payload["candidateId"]}
    first = client.post("/api/v1/events/ingest", headers=headers, json=payload)
    duplicate = client.post("/api/v1/events/ingest", headers=headers, json=payload)
    conflict = client.post(
        "/api/v1/events/ingest",
        headers=headers,
        json={**payload, "cameraId": "cam_02"},
    )

    assert first.status_code == 201
    assert duplicate.status_code == 200
    assert duplicate.json()["status"] == "DUPLICATE_IGNORED"
    assert duplicate.json()["incident"]["id"] == first.json()["incident"]["id"]
    assert conflict.status_code == 409


def test_ingest_rejects_unknown_camera_and_event_type():
    unknown_camera = client.post(
        "/api/v1/events/ingest",
        headers=INGEST_HEADERS,
        json=candidate_payload("evt-camera-missing", camera_id="cam_999"),
    )
    unknown_event = client.post(
        "/api/v1/events/ingest",
        headers=INGEST_HEADERS,
        json={**candidate_payload("evt-event-unknown"), "eventType": "UNKNOWN"},
    )

    assert unknown_camera.status_code == 422
    assert unknown_event.status_code == 422


def test_ingest_rejects_candidate_id_longer_than_database_column():
    response = client.post(
        "/api/v1/events/ingest",
        headers=INGEST_HEADERS,
        json=candidate_payload("x" * 256),
    )
    assert response.status_code == 422


def test_ingest_rejects_unbounded_or_malformed_assessment_metadata():
    base = candidate_payload("evt-bounds")
    cases = [
        {**base, "confidence": float("inf")},
        {**base, "zoneId": "x" * 101},
        {**base, "cameraId": "../../secret"},
        {**base, "firstSeenAt": "2026-08-11T09:00:00Z"},
        {**base, "modelVersion": "bad version with spaces"},
    ]
    for payload in cases:
        # httpx refuses to serialize non-finite floats, so the unbounded case is
        # sent as a raw JSON body (Infinity) �?" the server must reject it with 422.
        if isinstance(payload.get("confidence"), float) and not math.isfinite(payload["confidence"]):
            body = json.dumps(payload, allow_nan=True)
            response = client.post(
                "/api/v1/events/ingest",
                headers={**INGEST_HEADERS, "Content-Type": "application/json"},
                content=body,
            )
        else:
            response = client.post("/api/v1/events/ingest", headers=INGEST_HEADERS, json=payload)
        assert response.status_code == 422, response.text


def test_ingest_artifact_ready_backfills_clip_after_alert():
    """Alert posted immediately (PENDING) then the rendered clip is attached."""
    payload = candidate_payload("evt-backfill-001", event_type="ABANDONED_OBJECT")
    payload["artifact"] = {"available": False, "redactionStatus": "PENDING"}
    ingest = client.post("/api/v1/events/ingest", headers=INGEST_HEADERS, json=payload)
    assert ingest.status_code == 201
    incident_id = ingest.json()["incident"]["id"]
    assert ingest.json()["incident"]["redaction_status"] == "PENDING"
    assert ingest.json()["incident"]["artifact_url"] is None

    clip_url = f"/evidence/evt-backfill-001.mp4"
    ready = client.post(
        f"/api/v1/events/{incident_id}/artifact-ready",
        headers=INGEST_HEADERS,
        json={"uri": clip_url, "redactionStatus": "COMPLETE"},
    )
    assert ready.status_code == 200
    incident = ready.json()
    assert incident["artifact_url"] == clip_url
    assert incident["redaction_status"] == "COMPLETE"


def test_ingest_artifact_ready_requires_auth_and_existing_incident():
    ready = client.post(
        "/api/v1/events/999999/artifact-ready",
        headers=INGEST_HEADERS,
        json={"uri": "/evidence/x.mp4", "redactionStatus": "COMPLETE"},
    )
    assert ready.status_code == 404
    unauth = client.post(
        "/api/v1/events/1/artifact-ready",
        json={"uri": "/evidence/x.mp4", "redactionStatus": "COMPLETE"},
    )
    assert unauth.status_code == 401


def test_stream_clock_register_and_list():
    post = client.post(
        "/api/v1/stream/clock",
        headers=INGEST_HEADERS,
        json={"cameraId": "cam_02", "epoch": 1234.5, "duration": 73.0},
    )
    assert post.status_code == 200
    assert post.json()["camera_id"] == 2
    clocks = client.get("/api/v1/stream/clock").json()
    entry = next((clock for clock in clocks if clock["camera_id"] == 2), None)
    assert entry is not None
    assert entry["epoch"] == 1234.5
    assert entry["duration"] == 73.0


def test_stream_clock_requires_auth_and_valid_camera():
    unauth = client.post(
        "/api/v1/stream/clock",
        json={"cameraId": "cam_01", "epoch": 1.0, "duration": 10.0},
    )
    assert unauth.status_code == 401
    unknown = client.post(
        "/api/v1/stream/clock",
        headers=INGEST_HEADERS,
        json={"cameraId": "cam_999", "epoch": 1.0, "duration": 10.0},
    )
    assert unknown.status_code == 422
