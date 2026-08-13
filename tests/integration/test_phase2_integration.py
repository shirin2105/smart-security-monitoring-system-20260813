import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.cv.worker import CVWorker
from app.publisher.http_publisher import HttpEventPublisher


def test_phase2_end_to_end_flow():
    client = TestClient(app)
    # Test health endpoints
    res_live = client.get("/health/live")
    assert res_live.status_code == 200
    assert res_live.json()["status"] == "ALIVE"

    res_ready = client.get("/health/ready")
    assert res_ready.status_code == 200
    assert res_ready.json()["status"] == "READY"

    res_cam = client.get("/api/v1/cameras/cam_01/health")
    assert res_cam.status_code == 200
    assert res_cam.json()["camera_id"] == "cam_01"
