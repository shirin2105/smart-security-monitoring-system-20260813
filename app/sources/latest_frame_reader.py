from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any


class LatestFrameReader:
    """Continuously drain a capture into a single replaceable frame slot."""

    def __init__(self, capture: Any, clock: Callable[[], str]):
        self.capture = capture
        self.clock = clock
        self._condition = threading.Condition()
        self._latest: tuple[int, Any, str] | None = None
        self._sequence = 0
        self._failed = False
        self._stopped = False
        self._thread = threading.Thread(target=self._read_loop, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def next_frame(self, last_sequence: int, should_stop: Callable[[], bool]) -> tuple[int, Any, str] | None:
        with self._condition:
            while not should_stop():
                if self._latest is not None and self._latest[0] > last_sequence:
                    return self._latest
                if self._failed or self._stopped:
                    return None
                self._condition.wait(timeout=0.05)
        return None

    def stop(self) -> None:
        with self._condition:
            self._stopped = True
            self._condition.notify_all()
        self.capture.release()
        self._thread.join(timeout=0.5)

    def _read_loop(self) -> None:
        while True:
            with self._condition:
                if self._stopped:
                    return
            ok, frame = self.capture.read()
            if not ok:
                with self._condition:
                    self._failed = True
                    self._condition.notify_all()
                return
            captured_at = self.clock()
            with self._condition:
                self._sequence += 1
                self._latest = (self._sequence, frame, captured_at)
                self._condition.notify_all()
