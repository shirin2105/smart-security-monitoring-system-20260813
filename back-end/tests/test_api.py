import os
import pytest

TEST_DB_PATH = "./test_security_monitoring.db"
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

from fastapi.testclient import TestClient
from app.db.database import init_db_and_seed
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
