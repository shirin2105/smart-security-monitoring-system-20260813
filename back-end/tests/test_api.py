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
        response = client.post("/api/v1/events/ingest", headers=INGEST_HEADERS, json=payload)
        assert response.status_code == 422
