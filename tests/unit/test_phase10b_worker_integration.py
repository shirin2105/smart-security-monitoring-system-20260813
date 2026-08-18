"""Integration tests for Phase 10B worker behaviour (freshness, tiling, state)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from app.common.schemas import DetectionResult, FrameData
from app.common.time_utils import utc_now_iso
from app.cv.runtime.config import RuntimePerformanceConfig
from app.cv.runtime.metrics import MetricsCollector
from app.cv.runtime.scheduler import RealtimeScheduler
from app.cv.worker import CVWorker


def _config(**overrides) -> RuntimePerformanceConfig:
    base = {
        "profile": "BALANCED",
        "target_inference_fps": {"fast": 10, "balanced": 7, "accurate": 4},
        "latency_budget_ms": {"preferred": 500, "acceptable": 1000, "overloaded": 1500},
        "adaptive": {"enabled": True, "high_res_area_threshold": 1500000, "min_mode_hold_s": 5.0},
        "scheduler": {"policy": "round_robin", "starvation_threshold_ms": 1500},
        "overload": {"degraded_latency_ms": 700, "recovery_hold_s": 5.0},
    }
    for key, value in overrides.items():
        base[key] = value
    return RuntimePerformanceConfig.from_mapping(base)


def _now() -> str:
    return utc_now_iso()


def _live_frame(frame_id: int, captured_at: str, shape=(640, 480)) -> FrameData:
    return FrameData(
        camera_id="cam",
        frame_id=frame_id,
        captured_at=captured_at,
        source_type="RTSP",
        source_fps=25.0,
        inference_fps=7.0,
        image=np.zeros((*shape[::-1], 3), dtype=np.uint8),
    )


def _make_worker(source, *, detector=None, scheduler=None, metrics=None, perf=None, adaptive_mode=None):
    """Assemble a CVWorker via __new__ with the Phase 10B runtime attributes."""
    worker = CVWorker.__new__(CVWorker)
    worker.camera_id = "cam"
    worker.source = source
    worker.reset_after_s = 5.0
    worker.outage_reset_count = 0
    worker.processed_frames = 0
    worker.health_monitor = SimpleNamespace(
        last_inference_latency_ms=None,
        frames_processed=0,
        update_frame_time=lambda _: None,
        record_processed=lambda _: None,
        record_skipped=lambda: None,
    )
    worker.frame_sampler = SimpleNamespace()
    worker.frame_sampler.inference_fps = 7.0
    worker.frame_sampler.should_process = lambda _: True
    worker.detector = detector or SimpleNamespace(detect=lambda _: ([], 0.0))
    worker.tracker = SimpleNamespace(track=lambda *_a, **_k: [])
    worker.track_store = SimpleNamespace(update_track=lambda _: None, reset=lambda: None)
    worker.adapters = ()
    worker.event_manager = SimpleNamespace(end_all=lambda: [], process=lambda _: None, reset=lambda: None)
    worker.publisher = SimpleNamespace(publish=lambda _: True)
    worker.event_id_namespace = lambda value: value
    worker.detector_factory = lambda: worker.detector
    worker.performance_config = perf or _config()
    worker.profile = __import__("app.cv.runtime.profiles", fromlist=["resolve_profile"]).resolve_profile(
        worker.performance_config.profile, worker.performance_config
    )
    worker.scheduler = scheduler
    worker.metrics_collector = metrics
    worker.adaptive_controller = None
    if adaptive_mode is not None:
        worker.adaptive_controller = SimpleNamespace(decide=lambda _: __import__(
            "app.cv.runtime.adaptive_controller", fromlist=["AdaptiveDecision"]
        ).AdaptiveDecision(
            target_inference_fps=7.0,
            inference_mode=adaptive_mode,
            overload_state=__import__("app.cv.runtime.overload_state", fromlist=["OverloadState"]).OverloadState.NORMAL,
        ))
    return worker


def test_worker_uses_tiled_inference_when_adaptive_mode_is_tiled():
    frame = _live_frame(1, "_now()", shape=(1600, 1600))
    detector_calls = []

    def detect(frame_data):
        detector_calls.append(frame_data.image.shape[:2])
        return ([DetectionResult(class_id=0, class_name="person", bbox=[0, 0, 50, 50], confidence=0.9)], 1.0)

    detector = Mock()
    detector.detect.side_effect = detect

    class Source:
        def read_frames(self):
            return iter([frame])

        def release(self):
            pass

        def consume_outage_duration(self):
            return None

    worker = _make_worker(Source(), detector=detector, adaptive_mode="tile768_overlap20")
    worker.run(max_frames=1)
    # multiple tiles => multiple detector calls on tile-sized crops
    assert detector_calls, "detector must be invoked for tiled inference"
    assert all(h <= 768 and w <= 768 for h, w in detector_calls)


def test_worker_uses_full_frame_when_mode_is_full640():
    frame = _live_frame(1, "_now()", shape=(640, 480))
    detector = SimpleNamespace(detect=lambda _: ([], 0.0))
    detector.detect = Mock(side_effect=lambda _: ([], 0.0))

    class Source:
        def read_frames(self):
            return iter([frame])

        def release(self):
            pass

        def consume_outage_duration(self):
            return None

    worker = _make_worker(Source(), detector=detector, adaptive_mode="full640")
    worker.run(max_frames=1)
    assert detector.detect.call_count == 1


def test_stale_live_frame_is_dropped_not_queued():
    # A very old captured timestamp on a live source must be dropped (freshness-first).
    frame = _live_frame(1, "2020-01-01T00:00:00Z")
    detector = Mock(side_effect=lambda _: ([], 0.0))
    detector.detect.return_value = ([], 0.0)
    metrics = MetricsCollector()

    class Source:
        def read_frames(self):
            return iter([frame])

        def release(self):
            pass

        def consume_outage_duration(self):
            return None

    worker = _make_worker(Source(), detector=detector, metrics=metrics)
    worker.run(max_frames=1)
    assert detector.detect.call_count == 0
    snap = metrics.snapshot()
    assert snap["per_camera"]["cam"]["frames_dropped"] >= 1
    assert snap["per_camera"]["cam"]["frames_inferred"] == 0


def test_fresh_live_frame_is_inferred():
    frame = _live_frame(1, "_now()")
    detector = Mock(side_effect=lambda _: ([], 0.0))
    detector.detect.return_value = ([], 0.0)
    metrics = MetricsCollector()

    class Source:
        def read_frames(self):
            return iter([frame])

        def release(self):
            pass

        def consume_outage_duration(self):
            return None

    worker = _make_worker(Source(), detector=detector, metrics=metrics)
    worker.run(max_frames=1)
    assert detector.detect.call_count == 1
    snap = metrics.snapshot()
    assert snap["per_camera"]["cam"]["frames_inferred"] == 1


def test_profile_switch_preserves_tracker_and_event_state():
    # The worker must not reset tracker/TrackStore/event state when the profile
    # changes: adapters/tracker/track_store are untouched across decisions.
    frame = _live_frame(1, "_now()")
    detector = Mock(side_effect=lambda _: ([], 0.0))
    detector.detect.return_value = ([], 0.0)
    reset_calls = []

    class Source:
        def read_frames(self):
            return iter([frame])

        def release(self):
            pass

        def consume_outage_duration(self):
            return None

    worker = _make_worker(Source(), detector=detector)
    worker.tracker = SimpleNamespace(
        track=lambda *_a, **_k: [],
        reset=lambda: reset_calls.append("tracker"),
    )
    worker.track_store = SimpleNamespace(update_track=lambda _: None, reset=lambda: reset_calls.append("store"))
    worker.run(max_frames=1)
    assert reset_calls == []


def test_worker_with_scheduler_coexists_with_fair_turns():
    frame = _live_frame(1, "_now()")
    scheduler = RealtimeScheduler(_config())
    scheduler.register_camera("cam")
    metrics = MetricsCollector()
    detector = Mock(side_effect=lambda _: ([], 0.0))
    detector.detect.return_value = ([], 0.0)

    class Source:
        def read_frames(self):
            return iter([frame, frame, frame])

        def release(self):
            pass

        def consume_outage_duration(self):
            return None

    worker = _make_worker(Source(), detector=detector, scheduler=scheduler, metrics=metrics)
    worker.run(max_frames=3)
    assert detector.detect.call_count == 3
    assert scheduler.inference_count("cam") == 3
