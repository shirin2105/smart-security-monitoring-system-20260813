from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging
import os
import threading
import time
from collections.abc import AsyncGenerator, Callable
from typing import Any

import cv2
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

logger = logging.getLogger("webcam_stream_server")


def default_capture_opener(index: int | str) -> cv2.VideoCapture:
    """Open video capture with platform-appropriate backends."""
    if isinstance(index, str) and not index.isdigit():
        return cv2.VideoCapture(index)

    dev_idx = int(index)
    if os.name == "nt":
        for backend in [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]:
            cap = cv2.VideoCapture(dev_idx, backend)
            if cap.isOpened():
                return cap
            cap.release()
        return cv2.VideoCapture()
    return cv2.VideoCapture(dev_idx)


class WebcamCaptureManager:
    """Manages single-owner webcam access and background JPEG frame encoding."""

    def __init__(
        self,
        device_index: int | str = 0,
        target_fps: float = 15.0,
        jpeg_quality: int = 80,
        capture_factory: Callable[[int | str], Any] | None = None,
    ) -> None:
        self.device_index = device_index
        self.target_fps = max(1.0, min(float(target_fps), 60.0))
        self.jpeg_quality = max(10, min(int(jpeg_quality), 100))
        self._capture_factory = capture_factory or default_capture_opener
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._cap: Any = None
        self._latest_jpeg: bytes | None = None
        self._is_opened: bool = False
        self._last_frame_time: float = 0.0

    def start(self) -> bool:
        """Start the background frame capture loop."""
        if self._thread and self._thread.is_alive():
            return self._is_opened

        self._stop_event.clear()
        self._cap = self._capture_factory(self.device_index)
        if not self._cap or not self._cap.isOpened():
            logger.error("Failed to open webcam device %s", self.device_index)
            self._is_opened = False
            if self._cap:
                self._cap.release()
                self._cap = None
            return False

        self._is_opened = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("Webcam capture started on device %s at %.1f fps", self.device_index, self.target_fps)
        return True

    def stop(self) -> None:
        """Stop background capture and release the camera device."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None

        with self._lock:
            if self._cap is not None:
                self._cap.release()
                self._cap = None
            self._is_opened = False
            self._latest_jpeg = None
        logger.info("Webcam capture stopped and device released")

    def is_opened(self) -> bool:
        with self._lock:
            return self._is_opened

    def get_latest_jpeg(self) -> bytes | None:
        with self._lock:
            return self._latest_jpeg

    def _capture_loop(self) -> None:
        frame_interval = 1.0 / self.target_fps
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]

        while not self._stop_event.is_set():
            start_time = time.monotonic()
            if self._cap is None or not self._cap.isOpened():
                break

            ret, frame = self._cap.read()
            if not ret or frame is None:
                time.sleep(0.05)
                continue

            success, encoded_buf = cv2.imencode(".jpg", frame, encode_params)
            if success:
                jpeg_bytes = encoded_buf.tobytes()
                with self._lock:
                    self._latest_jpeg = jpeg_bytes
                    self._last_frame_time = time.time()

            elapsed = time.monotonic() - start_time
            sleep_time = max(0.0, frame_interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)


def create_webcam_server(
    device_index: int | str = 0,
    camera_id: str = "3",
    target_fps: float = 15.0,
    jpeg_quality: int = 80,
    capture_factory: Callable[[int | str], Any] | None = None,
) -> FastAPI:
    """Create a FastAPI application serving MJPEG streams with CORS and health checks."""
    manager = WebcamCaptureManager(
        device_index=device_index,
        target_fps=target_fps,
        jpeg_quality=jpeg_quality,
        capture_factory=capture_factory,
    )

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        manager.start()
        yield
        manager.stop()

    app = FastAPI(
        title="Webcam MJPEG Stream Server",
        description="Single-device owner HTTP MJPEG stream server for live camera feeds",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.manager = manager
    app.state.camera_id = str(camera_id)

    @app.get("/healthz")
    def healthz() -> JSONResponse:
        opened = manager.is_opened()
        content = {
            "status": "ok" if opened else "error",
            "device_open": opened,
            "camera_id": app.state.camera_id,
            "device_index": str(device_index),
        }
        status_code = status.HTTP_200_OK if opened else status.HTTP_503_SERVICE_UNAVAILABLE
        return JSONResponse(status_code=status_code, content=content)

    @app.get("/cameras/{req_camera_id}/stream")
    def camera_stream(req_camera_id: str):
        if not manager.is_opened():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"error": "webcam not available", "camera_id": req_camera_id},
            )

        def mjpeg_generator():
            interval = 1.0 / manager.target_fps
            while manager.is_opened():
                frame = manager.get_latest_jpeg()
                if frame is not None:
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        + f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii")
                        + frame
                        + b"\r\n"
                    )
                time.sleep(interval)

        headers = {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Access-Control-Allow-Origin": "*",
        }
        return StreamingResponse(
            mjpeg_generator(),
            media_type="multipart/x-mixed-replace; boundary=frame",
            headers=headers,
        )

    return app


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(description="Live Webcam MJPEG Stream Server")
    parser.add_argument("--index", default=0, help="Webcam device index (default: 0) or RTSP URL")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8081, help="Bind port (default: 8081)")
    parser.add_argument("--camera-id", default="3", help="Camera ID exposed in URLs (default: 3)")
    parser.add_argument("--fps", type=float, default=15.0, help="Target FPS (default: 15.0)")
    parser.add_argument("--quality", type=int, default=80, help="JPEG quality 1-100 (default: 80)")
    args = parser.parse_args()

    dev_index: int | str = int(args.index) if str(args.index).isdigit() else args.index
    server_app = create_webcam_server(
        device_index=dev_index,
        camera_id=args.camera_id,
        target_fps=args.fps,
        jpeg_quality=args.quality,
    )
    uvicorn.run(server_app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
