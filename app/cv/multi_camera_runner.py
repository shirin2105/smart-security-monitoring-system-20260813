"""Bounded multi-camera supervision with a shared, fair, serialized detector.

Phase 10B replaces naive lock contention with a shared ``RealtimeScheduler``
that grants detector turns round-robin/weighted so no camera starves another.
A shared ``MetricsCollector`` aggregates per-camera and global metrics.
"""

from __future__ import annotations

import inspect
import threading
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from app.config import settings
from app.cv.detector import DEIMv2Detector
from app.cv.runtime.config import RuntimePerformanceConfig
from app.cv.runtime.metrics import MetricsCollector
from app.cv.runtime.scheduler import RealtimeScheduler
from app.cv.worker import CVWorker


class LockedDetector:
    def __init__(self, detector: Any):
        self._detector = detector
        self._lock = threading.Lock()

    def detect(self, frame_data):
        with self._lock:
            return self._detector.detect(frame_data)


class MultiCameraRunner:
    def __init__(
        self,
        camera_configs: Iterable[dict] | None = None,
        max_workers: int = 6,
        detector: Any | None = None,
        worker_factory: Callable[..., Any] = CVWorker,
        performance_config: RuntimePerformanceConfig | None = None,
        scheduler: RealtimeScheduler | None = None,
        metrics: MetricsCollector | None = None,
    ):
        self.camera_configs = list(camera_configs if camera_configs is not None else settings.cameras)
        self.max_workers = max(1, min(int(max_workers), 6))
        model_cfg = settings.detector_config
        shared = detector if detector is not None else DEIMv2Detector(**model_cfg)
        self.detector = LockedDetector(shared)
        self.worker_factory = worker_factory
        self.performance_config = performance_config or RuntimePerformanceConfig.from_mapping(settings.runtime_performance)
        self.metrics = metrics or MetricsCollector()
        self.scheduler = scheduler or RealtimeScheduler(self.performance_config, metrics=self.metrics)

    def run(self, max_frames: int | None = None) -> dict[str, dict]:
        enabled = [cfg for cfg in self.camera_configs if cfg.get("enabled", True)][:6]
        results: dict[str, dict] = {}
        for cfg in enabled:
            self.scheduler.register_camera(str(cfg["camera_id"]))

        def execute(cfg: dict):
            kwargs: dict[str, Any] = {
                "camera_id": cfg["camera_id"],
                "source_uri": cfg.get("source_uri"),
                "camera_config": cfg,
                "detector": self.detector,
            }
            if self._factory_accepts("scheduler"):
                kwargs["scheduler"] = self.scheduler
            if self._factory_accepts("performance_config"):
                kwargs["performance_config"] = self.performance_config
            if self._factory_accepts("metrics"):
                kwargs["metrics"] = self.metrics
            worker = self.worker_factory(**kwargs)
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

    def _factory_accepts(self, param: str) -> bool:
        try:
            signature = inspect.signature(self.worker_factory)
        except (TypeError, ValueError):
            return False
        if param in signature.parameters:
            return True
        return any(p.kind == inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values())

    def metrics_snapshot(self) -> dict[str, Any]:
        return self.metrics.snapshot()
