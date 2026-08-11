"""Bounded multi-camera supervision with one lock-protected detector instance."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from app.config import settings
from app.cv.detector import DEIMv2Detector
from app.cv.worker import CVWorker


class LockedDetector:
    def __init__(self, detector: Any):
        self._detector = detector
        self._lock = threading.Lock()

    def detect(self, frame_data):
        with self._lock:
            return self._detector.detect(frame_data)


class MultiCameraRunner:
    def __init__(self, camera_configs: Iterable[dict] | None = None, max_workers: int = 6,
                 detector: Any | None = None, worker_factory: Callable[..., Any] = CVWorker):
        self.camera_configs = list(camera_configs if camera_configs is not None else settings.cameras)
        self.max_workers = max(1, min(int(max_workers), 6))
        model_cfg = settings.detector_config
        shared = detector if detector is not None else DEIMv2Detector(**model_cfg)
        self.detector = LockedDetector(shared)
        self.worker_factory = worker_factory

    def run(self, max_frames: int | None = None) -> dict[str, dict]:
        enabled = [cfg for cfg in self.camera_configs if cfg.get("enabled", True)][:6]
        results: dict[str, dict] = {}

        def execute(cfg: dict):
            worker = self.worker_factory(camera_id=cfg["camera_id"], source_uri=cfg.get("source_uri"),
                                         detector=self.detector)
            return worker.run(max_frames=max_frames)

        with ThreadPoolExecutor(max_workers=min(self.max_workers, max(1, len(enabled)))) as pool:
            futures = {pool.submit(execute, cfg): cfg["camera_id"] for cfg in enabled}
            for future in as_completed(futures):
                camera_id = futures[future]
                try:
                    results[camera_id] = {"status": "completed", "events": future.result()}
                except Exception as exc:  # one camera must not terminate its peers
                    results[camera_id] = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
        return results
