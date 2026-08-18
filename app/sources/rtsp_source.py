from __future__ import annotations

import threading
import time
from collections.abc import Callable, Generator
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import cv2

from app.common.schemas import FrameData
from app.common.time_utils import parse_iso_timestamp
from app.sources.base import BaseVideoSource
from app.sources.latest_frame_reader import LatestFrameReader


def redact_rtsp_uri(uri: str) -> str:
    parts = urlsplit(uri)
    if not parts.username:
        return uri
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    return urlunsplit((parts.scheme, f"{parts.username}:***@{host}", parts.path, parts.query, parts.fragment))


def live_timestamp_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


class RTSPVideoSource(BaseVideoSource):
    """Pull-based RTSP reader: no queue is retained, so stale frame backlog cannot grow."""

    def __init__(
        self,
        camera_id: str,
        source_uri: str,
        inference_fps: float,
        config: dict[str, Any] | None = None,
        capture_factory: Callable[[str], Any] | None = None,
        stop_event: threading.Event | None = None,
        clock: Callable[[], str] = live_timestamp_iso,
    ):
        self.camera_id, self.source_uri, self.inference_fps = camera_id, source_uri, inference_fps
        config = config or {}
        reconnect, rtsp = config.get("reconnect", {}), config.get("rtsp", {})
        self.initial_backoff_s = float(reconnect.get("initial_backoff_s", 1.0))
        self.max_backoff_s = float(reconnect.get("max_backoff_s", 15.0))
        self.multiplier = float(reconnect.get("multiplier", 2.0))
        self.reconnect_enabled = bool(reconnect.get("enabled", True))
        self.open_timeout_ms = int(rtsp.get("open_timeout_ms", 5000))
        self.read_timeout_ms = int(rtsp.get("read_timeout_ms", 5000))
        self._capture_factory = capture_factory or cv2.VideoCapture
        self._uses_default_capture = capture_factory is None
        self._stop = stop_event or threading.Event()
        self._external_stop: threading.Event | None = None
        self._deadline: float | None = None
        self._clock, self._cap, self._released = clock, None, False
        self.connection_state, self.reconnect_count, self.consecutive_read_failures = "DISCONNECTED", 0, 0
        self.frames_received, self.frames_dropped, self._frame_id = 0, 0, 0
        self.read_decode_errors, self.last_reconnect_at = 0, None
        self.source_fps = self.processed_fps = 0.0
        self.session_id, self._outage_started, self._pending_outage_s = 0, None, None
        self._open_attempts = 0
        self._last_timestamp_s: float | None = None
        self._reader: LatestFrameReader | None = None
        self._reset_after_s: float | None = None
        self._outage_callback: Callable[[float], None] | None = None
        self._outage_notified = False
        if self.initial_backoff_s < 0 or self.max_backoff_s < 0 or self.multiplier < 1:
            raise ValueError("invalid RTSP reconnect policy")

    def configure_stop(self, stop_event: threading.Event | None, deadline: float | None) -> None:
        self._external_stop = stop_event
        self._deadline = deadline

    def configure_outage_handler(self, reset_after_s: float, callback: Callable[[float], None]) -> None:
        self._reset_after_s = reset_after_s
        self._outage_callback = callback

    def _should_stop(self) -> bool:
        return bool(
            self._stop.is_set()
            or (self._external_stop is not None and self._external_stop.is_set())
            or (self._deadline is not None and time.monotonic() >= self._deadline)
        )

    def _wait(self, delay_s: float) -> None:
        end = time.monotonic() + max(0.0, delay_s)
        while not self._should_stop():
            self._notify_long_outage()
            remaining = end - time.monotonic()
            if remaining <= 0:
                return
            self._stop.wait(min(remaining, 0.1))

    def _notify_long_outage(self) -> None:
        if (
            self._outage_started is None
            or self._outage_notified
            or self._reset_after_s is None
            or self._outage_callback is None
        ):
            return
        outage_s = time.monotonic() - self._outage_started
        if outage_s >= self._reset_after_s:
            self._outage_callback(outage_s)
            self._outage_notified = True

    def _open(self) -> bool:
        self.connection_state = "CONNECTING"
        self._open_attempts += 1
        if self._open_attempts > 1:
            self.reconnect_count += 1
        if self._uses_default_capture:
            cap = self._capture_factory()
            params = [
                cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,
                self.open_timeout_ms,
                cv2.CAP_PROP_READ_TIMEOUT_MSEC,
                self.read_timeout_ms,
            ]
            try:
                cap.open(self.source_uri, cv2.CAP_FFMPEG, params)
            except (TypeError, cv2.error):
                cap.open(self.source_uri)
        else:
            try:
                cap = self._capture_factory()
            except TypeError:
                cap = self._capture_factory(self.source_uri)
        for prop, value in (
            (getattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC", None), self.open_timeout_ms),
            (getattr(cv2, "CAP_PROP_READ_TIMEOUT_MSEC", None), self.read_timeout_ms),
        ):
            if prop is not None:
                try:
                    cap.set(prop, value)
                except Exception:
                    pass
        if cap is not None and not cap.isOpened():
            opener = getattr(cap, "open", None)
            if callable(opener):
                try:
                    opener(self.source_uri)
                except Exception:
                    pass
        if cap is not None and cap.isOpened():
            self._cap, self.connection_state, self.consecutive_read_failures = cap, "CONNECTED", 0
            self.session_id += 1
            if self.session_id > 1:
                self.last_reconnect_at = live_timestamp_iso()
            if self._outage_started is not None:
                outage_s = max(0.0, time.monotonic() - self._outage_started)
                self._pending_outage_s = None if self._outage_notified else outage_s
                self._outage_started = None
                self._outage_notified = False
            self._reader = LatestFrameReader(cap, self._clock)
            self._reader.start()
            return True
        if cap is not None:
            cap.release()
        self.connection_state = "DEGRADED"
        return False

    def _next_timestamp(self, value: str) -> str:
        timestamp_s = parse_iso_timestamp(value).timestamp()
        if self._last_timestamp_s is not None and timestamp_s < self._last_timestamp_s:
            timestamp_s = self._last_timestamp_s
            value = datetime.fromtimestamp(timestamp_s, UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
        self._last_timestamp_s = timestamp_s
        return value

    def read_frames(self) -> Generator[FrameData, None, None]:
        backoff = self.initial_backoff_s
        last_sequence = 0
        while not self._should_stop():
            if self._cap is None and not self._open():
                if not self.reconnect_enabled:
                    break
                self.connection_state = "RECONNECTING"
                self._wait(backoff)
                backoff = min(self.max_backoff_s, backoff * self.multiplier)
                continue
            assert self._reader is not None
            latest = self._reader.next_frame(last_sequence, self._should_stop)
            if latest is None:
                self.consecutive_read_failures += 1
                self.connection_state = "DEGRADED"
                self.read_decode_errors += 1
                self._outage_started = self._outage_started or time.monotonic()
                self._reader.stop()
                self._reader = None
                self._cap = None
                last_sequence = 0
                continue
            sequence, frame, captured_at = latest
            backoff = self.initial_backoff_s
            self.frames_received += sequence - last_sequence
            self.frames_dropped += max(0, sequence - last_sequence - 1)
            last_sequence = sequence
            self._frame_id += 1
            fps = float(self._cap.get(cv2.CAP_PROP_FPS) or 0.0)
            self.source_fps = fps
            yield FrameData(
                camera_id=self.camera_id,
                frame_id=self._frame_id,
                captured_at=self._next_timestamp(captured_at),
                source_type="RTSP",
                source_fps=fps,
                inference_fps=self.inference_fps,
                image=frame,
            )

    def release(self) -> None:
        self._stop.set()
        if self._released:
            return
        self._released = True
        if self._cap is not None:
            if self._reader is not None:
                self._reader.stop()
                self._reader = None
            else:
                self._cap.release()
            self._cap = None
        self.connection_state = "DISCONNECTED"

    def consume_outage_duration(self) -> float | None:
        outage, self._pending_outage_s = self._pending_outage_s, None
        return outage
