"""Typed Phase 10B runtime performance configuration.

Mirrors ``configs/runtime_performance.yaml``. Values are intentionally kept as
plain dicts (rather than nested models) so the YAML layout from the phase
spec is preserved verbatim and per-camera overrides merge cleanly.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _clamp_int(value: Any, minimum: int, default: int) -> int:
    try:
        return max(minimum, int(value))
    except (TypeError, ValueError):
        return default


def _clamp_float(value: Any, minimum: float, default: float) -> float:
    try:
        return max(minimum, float(value))
    except (TypeError, ValueError):
        return default


class LatencyBudget(BaseModel):
    """Preferred/acceptable/overloaded latency thresholds in milliseconds."""

    model_config = ConfigDict(frozen=True)

    preferred_ms: int = 500
    acceptable_ms: int = 1000
    overloaded_ms: int = 1500

    @classmethod
    def from_mapping(cls, value: dict[str, Any] | None) -> "LatencyBudget":
        value = value or {}
        preferred = _clamp_int(value.get("preferred"), 1, 500)
        acceptable = _clamp_int(value.get("acceptable"), preferred, 1000)
        overloaded = _clamp_int(value.get("overloaded"), acceptable, 1500)
        return cls(preferred_ms=preferred, acceptable_ms=acceptable, overloaded_ms=overloaded)

    def classify(self, latency_ms: float) -> str:
        """Classify a measured latency into preferred/acceptable/overloaded."""
        if latency_ms >= self.overloaded_ms:
            return "overloaded"
        if latency_ms >= self.acceptable_ms:
            return "acceptable"
        return "preferred"


class AdaptiveTilingConfig(BaseModel):
    """Rule for switching between full-frame and tiled inference."""

    model_config = ConfigDict(frozen=True)

    enabled: bool = True
    high_res_area_threshold: int = 1_500_000
    tile_profile: str = "tile768_overlap20"
    tile_size: int = 768
    overlap_ratio: float = 0.20
    min_mode_hold_s: float = 5.0

    @classmethod
    def from_mapping(cls, value: dict[str, Any] | None) -> "AdaptiveTilingConfig":
        value = value or {}
        threshold = _clamp_int(value.get("high_res_area_threshold"), 1, 1_500_000)
        tile_size = _clamp_int(value.get("tile_size", 768), 256, 768)
        overlap = _clamp_float(value.get("overlap_ratio", 0.20), 0.0, 0.95)
        hold = _clamp_float(value.get("min_mode_hold_s", 5.0), 0.0, 60.0)
        return cls(
            enabled=bool(value.get("enabled", True)),
            high_res_area_threshold=threshold,
            tile_profile=str(value.get("tile_profile", "tile768_overlap20")),
            tile_size=tile_size,
            overlap_ratio=overlap,
            min_mode_hold_s=hold,
        )


class SchedulerConfig(BaseModel):
    """Multi-camera fairness scheduling policy."""

    model_config = ConfigDict(frozen=True)

    policy: str = "round_robin"
    starvation_threshold_ms: int = 1500

    @classmethod
    def from_mapping(cls, value: dict[str, Any] | None) -> "SchedulerConfig":
        value = value or {}
        policy = str(value.get("policy", "round_robin")).lower()
        if policy not in {"round_robin", "weighted"}:
            policy = "round_robin"
        threshold = _clamp_int(value.get("starvation_threshold_ms"), 1, 60_000)
        return cls(policy=policy, starvation_threshold_ms=threshold)


class OverloadConfig(BaseModel):
    """Overload state machine timing."""

    model_config = ConfigDict(frozen=True)

    degraded_latency_ms: int = 700
    overloaded_latency_ms: int = 1500
    recovery_hold_s: float = 5.0
    min_degrade_hold_s: float = 2.0
    dropped_ratio_high: float = 0.30

    @classmethod
    def from_mapping(cls, value: dict[str, Any] | None, overloaded_ms: int = 1500) -> "OverloadConfig":
        value = value or {}
        degraded = _clamp_int(value.get("degraded_latency_ms", 700), 1, 60_000)
        overloaded = _clamp_int(value.get("overloaded_latency_ms", overloaded_ms), degraded, 60_000)
        hold = _clamp_float(value.get("recovery_hold_s", 5.0), 0.0, 300.0)
        degrade_hold = _clamp_float(value.get("min_degrade_hold_s", 2.0), 0.0, 300.0)
        ratio = _clamp_float(value.get("dropped_ratio_high", 0.30), 0.0, 1.0)
        return cls(
            degraded_latency_ms=degraded,
            overloaded_latency_ms=overloaded,
            recovery_hold_s=hold,
            min_degrade_hold_s=degrade_hold,
            dropped_ratio_high=ratio,
        )


class RuntimePerformanceConfig(BaseModel):
    """Top-level Phase 10B runtime performance configuration."""

    model_config = ConfigDict(frozen=True)

    profile: str = "BALANCED"
    target_inference_fps: dict[str, int] = Field(default_factory=lambda: {"fast": 10, "balanced": 7, "accurate": 4})
    latency_budget: LatencyBudget = Field(default_factory=LatencyBudget)
    adaptive: AdaptiveTilingConfig = Field(default_factory=AdaptiveTilingConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    overload: OverloadConfig = Field(default_factory=OverloadConfig)

    @classmethod
    def from_mapping(cls, value: dict[str, Any] | None, overrides: dict[str, Any] | None = None) -> "RuntimePerformanceConfig":
        """Build config from a raw YAML mapping with optional per-camera overrides."""
        value = value or {}
        merged = dict(value)
        if overrides:
            for key in ("profile", "target_inference_fps", "latency_budget_ms", "adaptive", "scheduler", "overload"):
                if key in overrides:
                    merged[key] = overrides[key]
        fps_map = merged.get("target_inference_fps") or {}
        target = {
            "fast": _clamp_int(fps_map.get("fast", 10), 1, 120),
            "balanced": _clamp_int(fps_map.get("balanced", 7), 1, 120),
            "accurate": _clamp_int(fps_map.get("accurate", 4), 1, 120),
        }
        budget = LatencyBudget.from_mapping(merged.get("latency_budget_ms"))
        return cls(
            profile=str(merged.get("profile", "BALANCED")),
            target_inference_fps=target,
            latency_budget=budget,
            adaptive=AdaptiveTilingConfig.from_mapping(merged.get("adaptive")),
            scheduler=SchedulerConfig.from_mapping(merged.get("scheduler")),
            overload=OverloadConfig.from_mapping(merged.get("overload"), budget.overloaded_ms),
        )

    def with_profile(self, profile: str) -> "RuntimePerformanceConfig":
        return self.model_copy(update={"profile": profile})
