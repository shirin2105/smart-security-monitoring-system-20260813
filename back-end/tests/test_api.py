import os

TEST_DB_PATH = "./test_security_monitoring.db"
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

from app.db.database import init_db_and_seed
from fastapi.testclient import TestClient

from app.main import app

# Ensure tables and seed data are created for SQLite test database
init_db_and_seed()

client = TestClient(app)

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
    # Get alerts
    res_alerts = client.get("/api/v1/alerts")
    assert res_alerts.status_code == 200
    incidents = res_alerts.json()
    assert len(incidents) > 0

    first_incident_id = incidents[0]["id"]

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
    payload = {
        "candidateId": "evt-test-001",
        "cameraId": "cam_01",
        "eventType": "ZONE_INTRUSION",
        "severity": "critical",
        "detectedAt": "2026-08-11T08:00:00Z",
        "bbox": [100, 80, 240, 260],
    }
    response = client.post("/api/v1/events/ingest", json=payload)
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
    payload = {
        "candidateId": "evt-crowd-001",
        "cameraId": "cam_02",
        "eventType": "CROWD_THRESHOLD",
        "severity": "HIGH",
    }
    response = client.post("/api/v1/events/ingest", json=payload)
    assert response.status_code == 201
    incident = response.json()["incident"]
    assert incident["event_type"] == "dam_dong"
    assert incident["severity"] == "high"
    assert incident["camera_id"] == 2
