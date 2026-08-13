from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.api.events_ingest import FrameTelemetryIn, router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_frame_telemetry_schema_includes_video_time():
    payload = FrameTelemetryIn(
        cameraId="cam_01",
        timestamp="2026-01-01T00:00:00Z",
        videoTime=12.34,
        frameSize=[1280, 720],
        tracks=[],
    )
    assert payload.videoTime == 12.34


@patch("app.services.ingest.manager.broadcast", new_callable=AsyncMock)
def test_ingest_telemetry_broadcasts_video_time(mock_broadcast):
    response = client.post(
        "/api/v1/events/telemetry",
        json={
            "cameraId": "cam_01",
            "timestamp": "2026-01-01T00:00:00Z",
            "videoTime": 5.67,
            "frameSize": [1280, 720],
            "tracks": [],
        },
    )
    assert response.status_code == 200
    assert response.json() == {"status": "OK"}
    mock_broadcast.assert_called_once()
    broadcast_data = mock_broadcast.call_args[0][0]
    assert broadcast_data["videoTime"] == 5.67
    assert broadcast_data["cameraId"] == "cam_01"
