"""Phase 10B realtime performance runtime: profiles, adaptive inference,
latency budgets, overload states, multi-camera fairness and metrics."""

from app.cv.runtime.adaptive_controller import AdaptiveDecision, AdaptiveInferenceController, AdaptiveSignal
from app.cv.runtime.config import RuntimePerformanceConfig
from app.cv.runtime.metrics import GlobalMetrics, MetricsCollector, PerCameraMetrics
from app.cv.runtime.overload_state import OverloadState, OverloadStateMachine
from app.cv.runtime.profiles import ProfileConfig, resolve_profile
from app.cv.runtime.scheduler import RealtimeScheduler
from app.cv.runtime.tiling import AdaptiveTiling, merge_detections, plan_tiles

__all__ = [
    "AdaptiveDecision",
    "AdaptiveInferenceController",
    "AdaptiveSignal",
    "AdaptiveTiling",
    "GlobalMetrics",
    "MetricsCollector",
    "OverloadState",
    "OverloadStateMachine",
    "PerCameraMetrics",
    "ProfileConfig",
    "RealtimeScheduler",
    "RuntimePerformanceConfig",
    "merge_detections",
    "plan_tiles",
    "resolve_profile",
]
