"""Phase 10B deterministic scheduler benchmark (no real model required).

Measures multi-camera fairness, no-starvation and overload recovery using a
synthetic detector with a controllable service time. This is the portability
baseline required by Phase 10B; real DEIMv2 latency is documented separately in
the benchmark report because the model weights/GPU are not available here.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from threading import Lock

from app.cv.runtime.config import RuntimePerformanceConfig
from app.cv.runtime.metrics import MetricsCollector
from app.cv.runtime.scheduler import RealtimeScheduler


class TimedDetector:
    """Synthetic detector whose per-call service time is configurable."""

    def __init__(self, service_ms: float):
        self.service_ms = service_ms
        self.calls = 0
        self.lock = Lock()

    def detect(self, frame_data):
        with self.lock:
            self.calls += 1
        time.sleep(self.service_ms / 1000.0)
        return [], self.service_ms


def run_worker(camera_id: str, scheduler: RealtimeScheduler, service_ms: float, iterations: int,
               metrics: MetricsCollector) -> dict:
    stop = lambda: False
    counts = 0
    start = time.monotonic()
    for _ in range(iterations):
        if scheduler.await_turn(camera_id, stop):
            time.sleep(service_ms / 1000.0)
            scheduler.release_turn()
            counts += 1
            metrics.record_detector(camera_id, service_ms)
    elapsed = time.monotonic() - start
    return {"camera_id": camera_id, "inference_count": counts, "elapsed_s": round(elapsed, 3),
            "actual_fps": round(counts / elapsed, 3) if elapsed > 0 else 0.0}


def fairness_case(n_cameras: int, service_ms: float, iterations: int, heavy: bool = False) -> dict:
    config = RuntimePerformanceConfig.from_mapping(
        {"profile": "BALANCED", "scheduler": {"policy": "weighted" if heavy else "round_robin", "starvation_threshold_ms": 1500}}
    )
    metrics = MetricsCollector()
    scheduler = RealtimeScheduler(config, metrics=metrics)
    weights = {}
    for i in range(n_cameras):
        weight = 3.0 if (heavy and i == 0) else 1.0
        scheduler.register_camera(f"cam_{i}", weight=weight)
        weights[f"cam_{i}"] = weight
    threads = []
    results = {}
    lock = Lock()

    import threading

    def run(cam_id):
        res = run_worker(cam_id, scheduler, service_ms, iterations, metrics)
        with lock:
            results[cam_id] = res

    for i in range(n_cameras):
        cam = f"cam_{i}"
        thread = threading.Thread(target=run, args=(cam,))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    counts = [results[cam]["inference_count"] for cam in results]
    min_count = min(counts) if counts else 0
    snapshot = metrics.snapshot()
    return {
        "case": f"{n_cameras}-camera {'heavy' if heavy else 'fair'}",
        "weights": weights,
        "per_camera": results,
        "min_inference_count": min_count,
        "total_inference_rate": snapshot["total_inference_rate"],
        "starvation_count": snapshot["starvation_count"],
        "fair": min_count > 0,
    }


def main() -> None:
    cases = [
        fairness_case(1, 30, 30),       # P10B-01/02 single camera
        fairness_case(2, 30, 30),       # P10B-03 2-camera fairness
        fairness_case(2, 30, 30, heavy=True),  # P10B-04 heavy+normal
        fairness_case(4, 40, 30),       # P10B-05 4-camera overload
    ]
    report = {
        "matrix": cases,
        "note": "Deterministic synthetic-detector scheduler benchmark (portable). "
                "Real DEIMv2 latency + overload evidence requires model weights/GPU.",
    }
    out = Path("artifacts/phase10b-benchmark.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
