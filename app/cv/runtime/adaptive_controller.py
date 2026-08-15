"""Deterministic adaptive inference controller (no ML/RL).

Consumes recent per-camera signals and produces a target inference FPS plus an
inference mode. Latency budget drives graceful degradation: drop stale frames,
reduce FPS, downgrade tiling, and never grow the queue.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.cv.runtime.config import RuntimePerformanceConfig
from app.cv.runtime.overload_state import OverloadState, OverloadStateMachine
from app.cv.runtime.profiles import ProfileConfig, FULL_FRAME_MODE, resolve_profile
from app.cv.runtime.tiling import AdaptiveTiling


@dataclass
class AdaptiveSignal:
    """Latest measurable per-camera inputs to the controller."""

    camera_id: str
    source_resolution_area: float = 0.0
    recent_detector_latency_ms: float = 0.0
    recent_pipeline_latency_ms: float = 0.0
    actual_fps: float = 0.0
    dropped_ratio: float = 0.0
    gpu_utilization: float | None = None
    has_active_event: bool = False


@dataclass
class AdaptiveDecision:
    """Controller output applied to the current frame."""

    target_inference_fps: float
    inference_mode: str
    overload_state: OverloadState


class AdaptiveInferenceController:
    """Per-camera controller producing FPS + mode decisions under a latency budget."""

    def __init__(
        self,
        config: RuntimePerformanceConfig,
        camera_id: str,
        profile: ProfileConfig | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._config = config
        self.camera_id = camera_id
        self.profile = profile or resolve_profile(config.profile, config)
        self._state_machine = OverloadStateMachine(config.overload, clock=clock)
        self._tiling = AdaptiveTiling(config, clock=clock)
        self.target_inference_fps = float(self.profile.target_inference_fps)

    @property
    def overload_state(self) -> OverloadState:
        return self._state_machine.state

    @property
    def inference_mode(self) -> str:
        return self._tiling.mode

    @property
    def transition_count(self) -> int:
        return self._state_machine.transition_count

    def reset(self) -> None:
        self._state_machine.reset()
        self._tiling.reset()
        self.target_inference_fps = float(self.profile.target_inference_fps)

    def decide(self, signal: AdaptiveSignal) -> AdaptiveDecision:
        """Produce a decision for the current signal."""
        state = self._state_machine.update(
            latency_ms=signal.recent_pipeline_latency_ms,
            dropped_ratio=signal.dropped_ratio,
            starvation=False,
            gpu_saturated=self._gpu_saturated(signal),
        )
        fps = self._select_fps(signal, state)
        load_allows_tiling = self._load_allows_tiling(state, signal)
        mode = self._tiling.select(
            signal.source_resolution_area,
            load_allows_tiling,
            self.profile.tiling_intent,
        )
        if state is OverloadState.OVERLOADED:
            mode = FULL_FRAME_MODE
            # Cap against the profile base, never the running target, so
            # sustained overload cannot compound FPS decay down toward 0.
            fps = min(fps, self.profile.target_inference_fps / 2.0)
        self.target_inference_fps = fps
        return AdaptiveDecision(
            target_inference_fps=fps,
            inference_mode=mode,
            overload_state=state,
        )

    def _gpu_saturated(self, signal: AdaptiveSignal) -> bool:
        util = signal.gpu_utilization
        return util is not None and float(util) >= 0.95

    def _load_allows_tiling(self, state: OverloadState, signal: AdaptiveSignal) -> bool:
        if state in (OverloadState.OVERLOADED, OverloadState.DEGRADED):
            return False
        latency = max(signal.recent_pipeline_latency_ms, signal.recent_detector_latency_ms)
        return latency <= float(self._config.latency_budget.preferred_ms)

    def _select_fps(self, signal: AdaptiveSignal, state: OverloadState) -> float:
        base = float(self.profile.target_inference_fps)
        if state is OverloadState.OVERLOADED:
            fps = base / 2.0
        elif state is OverloadState.DEGRADED:
            fps = base * 0.7
        elif state is OverloadState.RECOVERING:
            fps = base * 0.9
        else:
            fps = base
        if signal.has_active_event:
            fps = min(base + 2.0, fps + 1.0)
        fps = max(1.0, float(fps))
        budget = self._config.latency_budget
        if signal.recent_pipeline_latency_ms > budget.overloaded_ms:
            fps = max(1.0, min(fps, 2.0))
        return fps
