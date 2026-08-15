"""Unit tests for Phase 10B runtime performance components."""

from __future__ import annotations

import threading
import time
from unittest.mock import Mock

import numpy as np
import pytest

from app.common.schemas import DetectionResult, FrameData
from app.cv.runtime.adaptive_controller import AdaptiveInferenceController, AdaptiveSignal
from app.cv.runtime.config import RuntimePerformanceConfig
from app.cv.runtime.metrics import MetricsCollector, PerCameraMetrics
from app.cv.runtime.overload_state import OverloadState, OverloadStateMachine
from app.cv.runtime.profiles import (
    ADAPTIVE_MODE,
    FULL_FRAME_MODE,
    TILE_MODE,
    ProfileConfig,
    is_high_resolution,
    parse_per_camera_overrides,
    resolve_profile,
)
from app.cv.runtime.scheduler import RealtimeScheduler
from app.cv.runtime.tiling import AdaptiveTiling, infer_tiles, merge_detections, plan_tiles


class FakeClock:
    def __init__(self, start: float = 1000.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _config(**overrides) -> RuntimePerformanceConfig:
    base = {
        "profile": "BALANCED",
        "target_inference_fps": {"fast": 10, "balanced": 7, "accurate": 4},
        "latency_budget_ms": {"preferred": 500, "acceptable": 1000, "overloaded": 1500},
        "adaptive": {
            "enabled": True,
            "high_res_area_threshold": 1500000,
            "tile_profile": "tile768_overlap20",
            "min_mode_hold_s": 5.0,
        },
        "scheduler": {"policy": "round_robin", "starvation_threshold_ms": 1500},
        "overload": {"degraded_latency_ms": 700, "recovery_hold_s": 5.0},
    }
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key].update(value)
        else:
            base[key] = value
    return RuntimePerformanceConfig.from_mapping(base)


# --- profiles -------------------------------------------------------------


def test_profile_selection_defaults_to_balanced():
    profile = resolve_profile(None, _config())
    assert profile.name == "BALANCED"
    assert profile.target_inference_fps == 7
    assert profile.tiling_intent == ADAPTIVE_MODE


def test_fast_uses_full_frame_and_10fps():
    profile = resolve_profile("FAST", _config())
    assert profile.name == "FAST"
    assert profile.target_inference_fps == 10
    assert profile.tiling_intent == FULL_FRAME_MODE


def test_accurate_uses_tiling_and_4fps():
    profile = resolve_profile("ACCURATE", _config())
    assert profile.name == "ACCURATE"
    assert profile.target_inference_fps == 4
    assert profile.tiling_intent == TILE_MODE


def test_unknown_profile_falls_back_to_default():
    profile = resolve_profile("NOPE", _config())
    assert profile.name == "BALANCED"


def test_per_camera_profile_override_parsing():
    cam = {"camera_id": "cam", "performance": {"profile": "FAST"}}
    assert parse_per_camera_overrides(cam) == {"profile": "FAST"}
    assert parse_per_camera_overrides(None) == {}


def test_high_resolution_threshold():
    cfg = _config()
    assert is_high_resolution(1_500_000, cfg) is True
    assert is_high_resolution(900_000, cfg) is False


# --- overload state machine ------------------------------------------------


def test_state_transitions_normal_to_overloaded():
    clock = FakeClock()
    machine = OverloadStateMachine(_config().overload, clock=clock)
    assert machine.state is OverloadState.NORMAL
    machine.update(latency_ms=2000)
    clock.advance(3.0)  # debounce: overload must persist
    machine.update(latency_ms=2000)
    assert machine.state is OverloadState.OVERLOADED
    assert machine.transition_count == 1


def test_transient_spike_does_not_churn_state():
    clock = FakeClock()
    machine = OverloadStateMachine(_config().overload, clock=clock)
    machine.update(latency_ms=2000)
    assert machine.state is OverloadState.NORMAL  # single spike, debounced
    clock.advance(0.5)
    machine.update(latency_ms=100)  # recovers before debounce elapses
    assert machine.state is OverloadState.NORMAL
    assert machine.transition_count == 0


def test_latency_spike_enters_degraded_then_overloaded():
    clock = FakeClock()
    machine = OverloadStateMachine(_config().overload, clock=clock)
    machine.update(latency_ms=800)
    clock.advance(3.0)
    machine.update(latency_ms=800)
    assert machine.state is OverloadState.DEGRADED
    machine.update(latency_ms=2000)
    assert machine.state is OverloadState.OVERLOADED


def test_recovery_requires_hold_time_hysteresis():
    clock = FakeClock()
    cfg = _config(overload={"recovery_hold_s": 5.0})
    machine = OverloadStateMachine(cfg.overload, clock=clock)
    machine.update(latency_ms=2000)
    clock.advance(3.0)
    machine.update(latency_ms=2000)
    assert machine.state is OverloadState.OVERLOADED
    machine.update(latency_ms=100)
    assert machine.state is OverloadState.RECOVERING
    clock.advance(2.0)
    machine.update(latency_ms=100)
    assert machine.state is OverloadState.RECOVERING  # not yet held long enough
    clock.advance(4.0)
    machine.update(latency_ms=100)
    assert machine.state is OverloadState.NORMAL


def test_overloaded_cannot_flap_to_normal_immediately():
    clock = FakeClock()
    machine = OverloadStateMachine(_config().overload, clock=clock)
    machine.update(latency_ms=2000)
    clock.advance(3.0)
    machine.update(latency_ms=2000)
    machine.update(latency_ms=100)
    assert machine.state is OverloadState.RECOVERING
    assert machine.state is not OverloadState.NORMAL


def test_dropped_ratio_high_triggers_degraded():
    clock = FakeClock()
    machine = OverloadStateMachine(_config().overload, clock=clock)
    machine.update(latency_ms=100, dropped_ratio=0.9)
    clock.advance(3.0)
    machine.update(latency_ms=100, dropped_ratio=0.9)
    assert machine.state is OverloadState.DEGRADED


def test_gpu_saturation_is_overload():
    clock = FakeClock()
    machine = OverloadStateMachine(_config().overload, clock=clock)
    machine.update(latency_ms=100, gpu_saturated=True)
    clock.advance(3.0)
    machine.update(latency_ms=100, gpu_saturated=True)
    assert machine.state is OverloadState.OVERLOADED


# --- adaptive tiling -------------------------------------------------------


def test_tiling_high_res_with_load_uses_tiles():
    clock = FakeClock()
    tiler = AdaptiveTiling(_config(), clock=clock)
    mode = tiler.select(2_000_000, load_allows_tiling=True, profile_tiling=ADAPTIVE_MODE)
    assert mode == TILE_MODE


def test_tiling_high_res_without_load_uses_full():
    clock = FakeClock()
    tiler = AdaptiveTiling(_config(), clock=clock)
    mode = tiler.select(2_000_000, load_allows_tiling=False, profile_tiling=ADAPTIVE_MODE)
    assert mode == FULL_FRAME_MODE


def test_tiling_low_res_uses_full():
    clock = FakeClock()
    tiler = AdaptiveTiling(_config(), clock=clock)
    mode = tiler.select(900_000, load_allows_tiling=True, profile_tiling=ADAPTIVE_MODE)
    assert mode == FULL_FRAME_MODE


def test_tiling_min_hold_prevents_flapping():
    clock = FakeClock()
    tiler = AdaptiveTiling(_config(), clock=clock)
    assert tiler.select(2_000_000, True, ADAPTIVE_MODE) == TILE_MODE
    clock.advance(1.0)
    # load drops, but min hold time has not elapsed
    assert tiler.select(2_000_000, False, ADAPTIVE_MODE) == TILE_MODE
    clock.advance(6.0)
    assert tiler.select(2_000_000, False, ADAPTIVE_MODE) == FULL_FRAME_MODE


def test_fast_profile_forces_full_frame_tiling():
    clock = FakeClock()
    tiler = AdaptiveTiling(_config(), clock=clock)
    assert tiler.select(2_000_000, True, FULL_FRAME_MODE) == FULL_FRAME_MODE


def test_plan_tiles_large_frame_produces_tiles():
    frame = np.zeros((1600, 1600, 3), dtype=np.uint8)
    tiles = plan_tiles(frame, tile_size=768, overlap_ratio=0.20)
    assert len(tiles) > 1
    assert all(t.x2 > t.x1 and t.y2 > t.y1 for t in tiles)
    assert all(t.image.shape[2] == 3 for t in tiles)


def test_plan_tiles_small_frame_returns_empty():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    assert plan_tiles(frame, tile_size=768, overlap_ratio=0.20) == []


def test_merge_detections_deduplicates_duplicates():
    a = DetectionResult(class_id=0, class_name="person", bbox=[0, 0, 100, 100], confidence=0.9)
    b = DetectionResult(class_id=0, class_name="person", bbox=[5, 5, 105, 105], confidence=0.7)
    merged = merge_detections([a, b], iou_threshold=0.5)
    assert len(merged) == 1
    assert merged[0].confidence == 0.9


def test_merge_detections_keeps_distinct_objects():
    a = DetectionResult(class_id=0, class_name="person", bbox=[0, 0, 100, 100], confidence=0.9)
    b = DetectionResult(class_id=0, class_name="person", bbox=[500, 500, 600, 600], confidence=0.8)
    assert len(merge_detections([a, b], iou_threshold=0.5)) == 2


def test_infer_tiles_hands_frame_data_to_detector():
    """Regression: the real DEIMv2 detector expects FrameData, not raw numpy."""
    from app.common.schemas import FrameData

    frame = FrameData(
        camera_id="cam", frame_id=1, captured_at="2026-08-15T00:00:00Z",
        source_type="RTSP", source_fps=25.0, inference_fps=7.0,
        image=np.zeros((1600, 1600, 3), dtype=np.uint8),
    )
    received = []

    def detect(frame_data):
        received.append(frame_data)
        return ([], 0.0)

    detector = Mock()
    detector.detect.side_effect = detect
    detections, _ = infer_tiles(detector, frame, 768, 0.20, 0.5)
    assert received, "detector must be called"
    assert all(isinstance(fd, FrameData) for fd in received)
    assert all(fd.image.shape[0] <= 768 and fd.image.shape[1] <= 768 for fd in received)


# --- adaptive controller ---------------------------------------------------


def test_controller_balanced_default_fps_and_mode():
    clock = FakeClock()
    controller = AdaptiveInferenceController(_config(), "cam", clock=clock)
    decision = controller.decide(AdaptiveSignal(camera_id="cam", source_resolution_area=900_000, recent_pipeline_latency_ms=50))
    assert decision.target_inference_fps == pytest.approx(7)
    assert decision.inference_mode == FULL_FRAME_MODE
    assert decision.overload_state is OverloadState.NORMAL


def test_controller_overloaded_reduces_fps_and_forces_full_frame():
    clock = FakeClock()
    controller = AdaptiveInferenceController(_config(), "cam", clock=clock)
    signal = AdaptiveSignal(camera_id="cam", source_resolution_area=2_000_000, recent_pipeline_latency_ms=2000)
    controller.decide(signal)
    clock.advance(3.0)  # allow the overload debounce to elapse
    decision = controller.decide(signal)
    assert decision.overload_state is OverloadState.OVERLOADED
    assert decision.inference_mode == FULL_FRAME_MODE
    assert decision.target_inference_fps < 7


def test_controller_event_boost_increases_fps():
    clock = FakeClock()
    controller = AdaptiveInferenceController(_config(), "cam", clock=clock)
    base = controller.decide(AdaptiveSignal(camera_id="cam", recent_pipeline_latency_ms=50))
    boosted = controller.decide(AdaptiveSignal(camera_id="cam", recent_pipeline_latency_ms=50, has_active_event=True))
    assert boosted.target_inference_fps > base.target_inference_fps


def test_controller_profile_switch_preserves_state():
    clock = FakeClock()
    controller = AdaptiveInferenceController(_config(), "cam", clock=clock)
    signal = AdaptiveSignal(camera_id="cam", recent_pipeline_latency_ms=2000)
    controller.decide(signal)
    clock.advance(3.0)
    controller.decide(signal)
    assert controller.overload_state is OverloadState.OVERLOADED
    # switching profile must not reset temporal runtime state
    fast = resolve_profile("FAST", _config())
    controller.profile = fast
    decision = controller.decide(signal)
    assert decision.inference_mode == FULL_FRAME_MODE
    assert decision.overload_state is OverloadState.OVERLOADED


def test_controller_sustained_overload_does_not_decay_fps_to_zero():
    """Regression: FPS must never compound downward toward 0 under sustained load."""
    clock = FakeClock()
    controller = AdaptiveInferenceController(_config(), "cam", clock=clock)
    signal = AdaptiveSignal(camera_id="cam", recent_pipeline_latency_ms=2000)
    controller.decide(signal)
    clock.advance(3.0)
    for _ in range(20):
        clock.advance(1.0)
        decision = controller.decide(signal)
        assert decision.overload_state is OverloadState.OVERLOADED
        # Never decays toward 0 (previously compounded by 0.5 each frame).
        assert decision.target_inference_fps >= 1.0
    assert controller.target_inference_fps >= 1.0


# --- metrics ---------------------------------------------------------------


def test_per_camera_metrics_snapshot():
    metrics = PerCameraMetrics("cam")
    metrics.source_fps = 25.0
    metrics.target_inference_fps = 7.0
    metrics.frames_dropped = 2
    metrics.mark_infer()
    snap = metrics.snapshot()
    assert snap["camera_id"] == "cam"
    assert snap["frames_inferred"] == 1
    assert snap["dropped_ratio"] > 0


def test_collector_aggregates_global_metrics():
    collector = MetricsCollector()
    collector.camera("cam_a").mark_infer()
    collector.camera("cam_b").mark_infer()
    collector.record_detector("cam_a", 50.0)
    collector.record_detector("cam_b", 60.0)
    collector.record_drop("cam_a")
    snap = collector.snapshot()
    assert snap["camera_count"] == 2
    assert snap["total_frames_dropped"] == 1
    assert snap["per_camera"]["cam_a"]["frames_inferred"] == 1


# --- scheduler -------------------------------------------------------------


def test_round_robin_grants_fair_turns():
    scheduler = RealtimeScheduler(_config())
    scheduler.register_camera("a")
    scheduler.register_camera("b")
    stop = lambda: False
    assert scheduler.await_turn("a", stop) is True
    scheduler.release_turn()
    assert scheduler.await_turn("b", stop) is True
    scheduler.release_turn()
    assert scheduler.await_turn("a", stop) is True


def test_scheduler_prevents_starvation_after_threshold():
    # Camera "a" grabs the first turn and never releases. Camera "b" must still
    # be granted a turn within the starvation threshold (preemption), proving
    # no camera is starved by a greedy peer.
    scheduler = RealtimeScheduler(_config(scheduler={"starvation_threshold_ms": 500}))
    scheduler.register_camera("a")
    scheduler.register_camera("b")
    assert scheduler.await_turn("a", lambda: False) is True
    started = time.monotonic()
    assert scheduler.await_turn("b", lambda: False) is True
    elapsed = time.monotonic() - started
    assert elapsed < 5.0
    assert scheduler.starvation_count() >= 1


def test_weighted_ring_gives_heavier_camera_more_slots():
    scheduler = RealtimeScheduler(_config(scheduler={"policy": "weighted"}))
    scheduler.register_camera("heavy", weight=3.0)
    scheduler.register_camera("light", weight=1.0)
    assert scheduler.camera_ids.count("heavy") > scheduler.camera_ids.count("light")


def test_event_boost_preempts_waiting_peer():
    clock = FakeClock()
    scheduler = RealtimeScheduler(_config(scheduler={"starvation_threshold_ms": 1000}), clock=clock)
    scheduler.register_camera("a")
    scheduler.register_camera("b")
    scheduler.set_active_event("b", True)
    stop = lambda: False
    # a is cursor, but b has an active event -> b preempts
    assert scheduler.await_turn("b", stop) is True
    scheduler.release_turn()


def test_await_turn_returns_false_when_stopped():
    scheduler = RealtimeScheduler(_config())
    scheduler.register_camera("a")
    stop_called = []
    stop = lambda: stop_called.append(True) or True
    assert scheduler.await_turn("a", stop) is False


def test_unregister_removes_camera():
    scheduler = RealtimeScheduler(_config())
    scheduler.register_camera("a")
    scheduler.register_camera("b")
    scheduler.unregister_camera("a")
    assert "a" not in scheduler.camera_ids


def test_scheduler_concurrent_fairness_no_zero_fps():
    """Two threads must both make progress under the shared scheduler."""
    scheduler = RealtimeScheduler(_config(scheduler={"starvation_threshold_ms": 500}))
    scheduler.register_camera("a")
    scheduler.register_camera("b")
    counts = {"a": 0, "b": 0}
    lock = threading.Lock()

    def worker(cam: str) -> None:
        stop = lambda: False
        for _ in range(20):
            if scheduler.await_turn(cam, stop):
                time.sleep(0.001)
                with lock:
                    counts[cam] += 1
                scheduler.release_turn()

    threads = [threading.Thread(target=worker, args=(cam,)) for cam in ("a", "b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)
    assert counts["a"] > 0 and counts["b"] > 0
