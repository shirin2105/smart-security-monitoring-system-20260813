"""FAST / BALANCED / ACCURATE runtime profiles and resolution.

Production default is BALANCED. A profile only changes the *target* inference
rate and tiling intent; it never owns tracker/TrackStore/event state, so
switching profiles preserves all temporal state by construction.
"""

from __future__ import annotations

from typing import Any

from app.cv.runtime.config import RuntimePerformanceConfig

FULL_FRAME_MODE = "full640"
TILE_MODE = "tile768_overlap20"
ADAPTIVE_MODE = "adaptive"


class ProfileConfig:
    """Immutable profile description resolved against the live config."""

    __slots__ = ("name", "target_inference_fps", "tiling_intent", "description")

    def __init__(self, name: str, target_inference_fps: float, tiling_intent: str, description: str) -> None:
        self.name = name
        self.target_inference_fps = target_inference_fps
        self.tiling_intent = tiling_intent
        self.description = description

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"ProfileConfig({self.name}, fps={self.target_inference_fps}, tiling={self.tiling_intent})"


def resolve_profile(profile_name: str | None, config: RuntimePerformanceConfig) -> ProfileConfig:
    """Resolve a profile name against config, returning the effective profile.

    FAST -> full-frame only; BALANCED -> adaptive tiling; ACCURATE -> tiled.
    Target FPS is overridden by ``config.target_inference_fps`` when present so
    hardware tuning stays in configuration, not code.
    """
    name = str(profile_name or config.profile or "BALANCED").upper()
    if name not in {"FAST", "BALANCED", "ACCURATE"}:
        name = str(config.profile or "BALANCED").upper()
    fps_map = config.target_inference_fps or {}
    if name == "FAST":
        fps = float(fps_map.get("fast", 10))
        return ProfileConfig(name, fps, FULL_FRAME_MODE, "maximum throughput, whole-frame inference")
    if name == "ACCURATE":
        fps = float(fps_map.get("accurate", 4))
        return ProfileConfig(name, fps, TILE_MODE, "maximum recall, tiled inference")
    fps = float(fps_map.get("balanced", 7))
    return ProfileConfig(name, fps, ADAPTIVE_MODE, "balanced throughput/accuracy, adaptive tiling")


def profile_tiling_intent(profile: ProfileConfig) -> str:
    """Return the concrete default inference mode for a resolved profile."""
    return profile.tiling_intent


def is_high_resolution(area_px: float, config: RuntimePerformanceConfig) -> bool:
    """Return True when a scene exceeds the high-resolution area threshold."""
    return float(area_px) >= float(config.adaptive.high_res_area_threshold)


def profile_name(profile: ProfileConfig | None, config: RuntimePerformanceConfig) -> str:
    """Return the canonical profile name (default BALANCED)."""
    if profile is not None:
        return profile.name
    return str(getattr(config, "profile", "BALANCED")).upper()


def parse_per_camera_overrides(camera_config: dict[str, Any] | None) -> dict[str, Any]:
    """Extract a per-camera ``performance`` override block, if any."""
    if not camera_config:
        return {}
    override = camera_config.get("performance")
    return override if isinstance(override, dict) else {}
