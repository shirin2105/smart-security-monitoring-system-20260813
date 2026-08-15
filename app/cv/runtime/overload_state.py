"""Overload state machine: NORMAL / DEGRADED / OVERLOADED / RECOVERING.

Uses hysteresis plus minimum hold times so a noisy latency spike cannot flap
the state between adjacent buckets, and recovery requires sustained good
metrics before returning to NORMAL.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Callable

from app.cv.runtime.config import OverloadConfig


class OverloadState(str, Enum):
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    OVERLOADED = "OVERLOADED"
    RECOVERING = "RECOVERING"


def _default_clock() -> float:
    return time.monotonic()


class OverloadStateMachine:
    """Deterministic, hysteresis-protected overload state machine."""

    def __init__(
        self,
        config: OverloadConfig | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._config = config or OverloadConfig()
        self._clock = clock or _default_clock
        self._state = OverloadState.NORMAL
        self._good_since: float | None = None
        self._bad_since: float | None = None
        self._pending_enter: OverloadState | None = None
        self.transition_count = 0

    @property
    def state(self) -> OverloadState:
        return self._state

    @property
    def name(self) -> str:
        return self._state.value

    def reset(self) -> None:
        """Return to NORMAL (e.g. after a long source outage)."""
        self._state = OverloadState.NORMAL
        self._good_since = None
        self._bad_since = None
        self._pending_enter = None

    def update(
        self,
        latency_ms: float,
        dropped_ratio: float = 0.0,
        starvation: bool = False,
        gpu_saturated: bool = False,
    ) -> OverloadState:
        """Advance the state from measured metrics and return the new state."""
        now = self._clock()
        degraded_ms = float(self._config.degraded_latency_ms)
        overloaded_ms = float(self._config.overloaded_latency_ms)
        dropped_high = float(dropped_ratio) >= self._config.dropped_ratio_high

        overloaded = float(latency_ms) >= overloaded_ms or starvation or gpu_saturated
        degraded = float(latency_ms) >= degraded_ms or dropped_high
        good = not degraded and not overloaded and float(latency_ms) < degraded_ms * 0.6

        if self._state is OverloadState.NORMAL:
            if degraded or overloaded:
                target = OverloadState.OVERLOADED if overloaded else OverloadState.DEGRADED
                self._track_pending_enter(target, now)
            else:
                self._bad_since = None
                self._pending_enter = None
        elif self._state is OverloadState.DEGRADED:
            if overloaded:
                self._enter(OverloadState.OVERLOADED, now)
            elif good:
                self._enter(OverloadState.RECOVERING, now)
        elif self._state is OverloadState.OVERLOADED:
            if not overloaded and not degraded:
                self._enter(OverloadState.RECOVERING, now)
        elif self._state is OverloadState.RECOVERING:
            if overloaded:
                self._enter(OverloadState.OVERLOADED, now)
            elif degraded:
                self._enter(OverloadState.DEGRADED, now)
            elif good and self._good_since is not None and (now - self._good_since) >= self._config.recovery_hold_s:
                self._enter(OverloadState.NORMAL, now)

        if good:
            self._good_since = self._good_since if self._good_since is not None else now
        else:
            self._good_since = None
        return self._state

    def _track_pending_enter(self, target: OverloadState, now: float) -> None:
        """Debounce upward transitions so a transient spike cannot churn state."""
        if self._pending_enter != target:
            self._pending_enter = target
            self._bad_since = now
            return
        if (now - self._bad_since) >= self._config.min_degrade_hold_s:
            self._enter(target, now)

    def _enter(self, state: OverloadState, now: float) -> None:
        if state is OverloadState.RECOVERING:
            self._good_since = now
        else:
            self._good_since = None
        if state is not self._state:
            self.transition_count += 1
        self._state = state
        self._bad_since = now
