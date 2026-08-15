"""Multi-camera realtime scheduler with fairness and no starvation.

Replaces naive lock contention with explicit round-robin (or weighted
round-robin) turn granting shared across worker threads. A camera that has
waited beyond ``starvation_threshold_ms`` is preemptively granted a turn so no
camera is starved by a greedy peer. ``MetricsCollector`` captures wait/fairness
signals for the per-camera and global metrics.
"""

from __future__ import annotations

import threading
import time
from typing import Callable

from app.cv.runtime.config import RuntimePerformanceConfig
from app.cv.runtime.metrics import MetricsCollector


def _default_clock() -> float:
    return time.monotonic()


class CameraSlot:
    __slots__ = ("camera_id", "weight", "tokens", "last_grant", "wait_started", "inference_count")

    def __init__(self, camera_id: str, weight: float) -> None:
        self.camera_id = camera_id
        self.weight = max(1.0, float(weight))
        self.tokens = int(round(self.weight))
        self.last_grant: float | None = None
        self.wait_started: float | None = None
        self.inference_count = 0


class RealtimeScheduler:
    """Shared, fair, serialized detector scheduler across cameras."""

    def __init__(
        self,
        config: RuntimePerformanceConfig | None = None,
        metrics: MetricsCollector | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        cfg = (config.scheduler if config is not None else None)
        self._policy = getattr(cfg, "policy", "round_robin") or "round_robin"
        self._starvation_threshold_s = (getattr(cfg, "starvation_threshold_ms", 1500) or 1500) / 1000.0
        self._clock = clock or _default_clock
        self._metrics = metrics or MetricsCollector()
        self._condition = threading.Condition()
        self._slots: dict[str, CameraSlot] = {}
        self._order: list[str] = []
        self._cursor = 0
        self._boost: set[str] = set()

    @property
    def policy(self) -> str:
        return self._policy

    @property
    def camera_ids(self) -> list[str]:
        with self._condition:
            return list(self._order)

    def register_camera(self, camera_id: str, weight: float = 1.0) -> None:
        with self._condition:
            if camera_id in self._slots:
                return
            slot = CameraSlot(camera_id, weight)
            self._slots[camera_id] = slot
            self._order.append(camera_id)
            for _ in range(slot.tokens - 1):
                self._order.append(camera_id)

    def unregister_camera(self, camera_id: str) -> None:
        with self._condition:
            self._slots.pop(camera_id, None)
            self._order = [cid for cid in self._order if cid != camera_id]
            self._boost.discard(camera_id)
            if self._cursor >= len(self._order):
                self._cursor = 0
            self._condition.notify_all()

    def set_active_event(self, camera_id: str, has_event: bool) -> None:
        with self._condition:
            if has_event:
                self._boost.add(camera_id)
            else:
                self._boost.discard(camera_id)

    def await_turn(self, camera_id: str, should_stop: Callable[[], bool]) -> bool:
        """Block until this camera is granted a detector turn.

        Returns False when the caller should stop. Granting is fair
        (round-robin/weighted) and anti-starvation: a camera waiting longer than
        the threshold preempts the cursor.
        """
        with self._condition:
            if camera_id not in self._slots:
                return False
            slot = self._slots[camera_id]
            if slot.wait_started is None:
                slot.wait_started = self._clock()
            while not should_stop():
                if self._grant(slot):
                    slot.last_grant = self._clock()
                    slot.inference_count += 1
                    self._metrics.camera(camera_id).scheduler_wait_ms = (
                        max(0.0, self._clock() - slot.wait_started) * 1000.0
                    )
                    slot.wait_started = None
                    return True
                self._condition.wait(timeout=0.05)
            return False

    def release_turn(self) -> None:
        """Advance the round-robin cursor so the next camera gets a turn."""
        with self._condition:
            if not self._order:
                return
            self._cursor = (self._cursor + 1) % len(self._order)
            self._condition.notify_all()

    def _grant(self, slot: CameraSlot) -> bool:
        if not self._order:
            return True
        index = self._cursor % len(self._order)
        expected = self._order[index]
        if slot.camera_id == expected:
            return True
        if slot.camera_id in self._boost:
            return True
        waited = self._clock() - slot.wait_started if slot.wait_started is not None else 0.0
        if waited >= self._starvation_threshold_s:
            try:
                self._cursor = self._order.index(slot.camera_id, 0, len(self._order))
            except ValueError:
                pass
            self._metrics.record_starvation()
            return True
        return False

    def inference_count(self, camera_id: str) -> int:
        with self._condition:
            slot = self._slots.get(camera_id)
            return slot.inference_count if slot is not None else 0

    def starvation_count(self) -> int:
        return self._metrics.global_metrics.starvation_count
