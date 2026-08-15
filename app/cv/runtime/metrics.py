"""Per-camera and global Phase 10B metrics.

Collector is designed for a shared multi-camera runtime, so mutations are
guarded by a lock and snapshots are shallow copies.
"""

from __future__ import annotations

import threading
import time
from typing import Any


class PerCameraMetrics:
    """Mutable per-camera counters/gauges for the scheduler and controller."""

    def __init__(self, camera_id: str) -> None:
        self.camera_id = camera_id
        self._lock = threading.Lock()
        self.source_fps: float = 0.0
        self.target_inference_fps: float = 0.0
        self.actual_inference_fps: float = 0.0
        self.detector_latency_ms: float = 0.0
        self.pipeline_latency_ms: float = 0.0
        self.frame_age_at_inference_ms: float = 0.0
        self.frames_received: int = 0
        self.frames_inferred: int = 0
        self.frames_dropped: int = 0
        self.frames_skipped: int = 0
        self.scheduler_wait_ms: float = 0.0
        self.profile: str = "BALANCED"
        self.inference_mode: str = "full640"
        self.overload_state: str = "NORMAL"
        self._infer_started_at: float | None = None

    def mark_infer(self) -> None:
        with self._lock:
            if self._infer_started_at is None:
                self._infer_started_at = time.monotonic()
            self.frames_inferred += 1
            elapsed = time.monotonic() - self._infer_started_at
            self.actual_inference_fps = self.frames_inferred / elapsed if elapsed > 0 else 0.0

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return self._snapshot_locked()

    def _snapshot_locked(self) -> dict[str, Any]:
        total = self.frames_inferred + self.frames_dropped + self.frames_skipped
        drop_ratio = (self.frames_dropped + self.frames_skipped) / total if total > 0 else 0.0
        return {
            "camera_id": self.camera_id,
            "source_fps": self.source_fps,
            "target_inference_fps": self.target_inference_fps,
            "actual_inference_fps": round(self.actual_inference_fps, 3),
            "detector_latency_ms": round(self.detector_latency_ms, 3),
            "pipeline_latency_ms": round(self.pipeline_latency_ms, 3),
            "frame_age_at_inference_ms": round(self.frame_age_at_inference_ms, 3),
            "frames_received": self.frames_received,
            "frames_inferred": self.frames_inferred,
            "frames_dropped": self.frames_dropped,
            "frames_skipped": self.frames_skipped,
            "dropped_ratio": round(drop_ratio, 4),
            "scheduler_wait_ms": round(self.scheduler_wait_ms, 3),
            "profile": self.profile,
            "inference_mode": self.inference_mode,
            "overload_state": self.overload_state,
        }


class GlobalMetrics:
    """Aggregated metrics across all cameras in a shared runtime."""

    def __init__(self) -> None:
        self.total_inference_count: int = 0
        self.total_detector_ms: float = 0.0
        self.starvation_count: int = 0
        self.total_frames_dropped: int = 0
        self.started_at: float = time.monotonic()

    @property
    def detector_utilization(self) -> float:
        elapsed = time.monotonic() - self.started_at
        return self.total_detector_ms / 1000.0 / elapsed if elapsed > 0 else 0.0

    def snapshot(self, camera_count: int, per_camera: dict[str, dict[str, Any]]) -> dict[str, Any]:
        total_rate = 0.0
        elapsed = time.monotonic() - self.started_at
        if elapsed > 0:
            total_rate = self.total_inference_count / elapsed
        return {
            "total_inference_rate": round(total_rate, 3),
            "detector_utilization": round(self.detector_utilization, 4),
            "camera_count": camera_count,
            "starvation_count": self.starvation_count,
            "total_frames_dropped": self.total_frames_dropped,
            "per_camera": per_camera,
        }


class MetricsCollector:
    """Thread-safe collection of per-camera and global metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cameras: dict[str, PerCameraMetrics] = {}
        self.global_metrics = GlobalMetrics()

    def camera(self, camera_id: str) -> PerCameraMetrics:
        with self._lock:
            metrics = self._cameras.get(camera_id)
            if metrics is None:
                metrics = PerCameraMetrics(camera_id)
                self._cameras[camera_id] = metrics
            return metrics

    def record_starvation(self) -> None:
        with self._lock:
            self.global_metrics.starvation_count += 1

    def record_detector(self, camera_id: str, latency_ms: float) -> None:
        metrics = self.camera(camera_id)
        metrics.detector_latency_ms = latency_ms
        with self._lock:
            self.global_metrics.total_inference_count += 1
            self.global_metrics.total_detector_ms += max(0.0, latency_ms)

    def record_drop(self, camera_id: str) -> None:
        self.camera(camera_id).frames_dropped += 1
        with self._lock:
            self.global_metrics.total_frames_dropped += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            per_camera = {cid: metrics.snapshot() for cid, metrics in self._cameras.items()}
            return self.global_metrics.snapshot(len(self._cameras), per_camera)
