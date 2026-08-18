from __future__ import annotations

import asyncio
import time
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.webcam_stream_server import (
    WebcamCaptureManager,
    create_webcam_server,
)


class FakeVideoCapture:
    def __init__(self, frames: list[tuple[bool, np.ndarray | None]] | None = None, is_open: bool = True):
        self._frames = list(frames or [])
        self._is_open = is_open
        self.released = False

    def isOpened(self) -> bool:  # noqa: N802
        return self._is_open and not self.released

    def read(self) -> tuple[bool, np.ndarray | None]:
        if not self.isOpened():
            return False, None
        if self._frames:
            return self._frames.pop(0)
        # Default synthetic frame: 100x100 RGB image
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        return True, frame

    def release(self) -> None:
        self.released = True
        self._is_open = False


def test_capture_manager_lifecycle():
    fake_cap = FakeVideoCapture()
    manager = WebcamCaptureManager(
        device_index=0,
        target_fps=20.0,
        capture_factory=lambda _: fake_cap,
    )

    assert not manager.is_opened()
    assert manager.start() is True
    assert manager.is_opened() is True

    # Allow capture loop to acquire at least one frame
    for _ in range(20):
        if manager.get_latest_jpeg() is not None:
            break
        time.sleep(0.05)

    assert manager.get_latest_jpeg() is not None
    manager.stop()
    assert not manager.is_opened()
    assert fake_cap.released is True


def test_capture_manager_failed_open():
    fake_cap = FakeVideoCapture(is_open=False)
    manager = WebcamCaptureManager(
        device_index=99,
        capture_factory=lambda _: fake_cap,
    )
    assert manager.start() is False
    assert not manager.is_opened()
    assert manager.get_latest_jpeg() is None


def test_webcam_server_healthz_and_stream_success():
    app = create_webcam_server(
        device_index=0,
        camera_id="3",
        target_fps=20.0,
        capture_factory=lambda _: FakeVideoCapture(),
    )

    with TestClient(app) as client:
        # Test /healthz
        res = client.get("/healthz")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["device_open"] is True
        assert data["camera_id"] == "3"

    # Test stream generator directly with fresh capture
    app_direct = create_webcam_server(
        device_index=0,
        camera_id="3",
        capture_factory=lambda _: FakeVideoCapture(),
    )
    route_fn = None
    for route in app_direct.routes:
        if getattr(route, "path", "") == "/cameras/{req_camera_id}/stream":
            route_fn = route.endpoint
            break
    assert route_fn is not None
    app_direct.state.manager.start()
    for _ in range(20):
        if app_direct.state.manager.get_latest_jpeg() is not None:
            break
        time.sleep(0.05)

    streaming_res = route_fn("3")
    assert streaming_res.status_code == 200
    assert "multipart/x-mixed-replace" in streaming_res.media_type
    assert streaming_res.headers.get("Access-Control-Allow-Origin") == "*"

    chunk_gen = streaming_res.body_iterator
    first_chunk = asyncio.run(anext(chunk_gen))
    assert b"--frame" in first_chunk
    assert b"Content-Type: image/jpeg" in first_chunk
    app_direct.state.manager.stop()


def test_webcam_server_healthz_and_stream_unavailable():
    app = create_webcam_server(
        device_index=0,
        camera_id="3",
        target_fps=20.0,
        capture_factory=lambda _: FakeVideoCapture(is_open=False),
    )

    with TestClient(app) as client:
        res = client.get("/healthz")
        assert res.status_code == 503
        data = res.json()
        assert data["status"] == "error"
        assert data["device_open"] is False

        stream_res = client.get("/cameras/3/stream")
        assert stream_res.status_code == 503
