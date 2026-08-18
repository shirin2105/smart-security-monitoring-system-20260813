import threading
import time

import cv2
import numpy as np

from app.common.time_utils import parse_iso_timestamp
from app.sources.factory import create_video_source
from app.sources.latest_frame_reader import LatestFrameReader
from app.sources.rtsp_source import RTSPVideoSource, redact_rtsp_uri


class FakeCapture:
    def __init__(self, reads=None, opened=True):
        self.reads, self.opened, self.released = list(reads or []), opened, False

    def isOpened(self):  # noqa: N802 - mirrors OpenCV's public API
        return self.opened

    def set(self, *_):
        return True

    def get(self, *_):
        return 0

    def read(self):
        return self.reads.pop(0) if self.reads else (False, None)

    def release(self):
        self.released = True
        self.opened = False


class CaptureFactory:
    def __init__(self, captures):
        self.captures = list(captures)
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.captures.pop(0)


def test_factory_maps_rtsp_without_passing_uri_to_mp4():
    source = create_video_source(
        {"camera_id": "rtsp", "source_type": "RTSP", "source_uri": "rtsp://x", "inference_fps": 5}
    )
    assert isinstance(source, RTSPVideoSource)


def test_rtsp_yields_wall_clock_monotonic_frame_ids_and_idempotent_release():
    capture = FakeCapture([(True, np.zeros((2, 2, 3))), (False, None)])
    source = RTSPVideoSource(
        "cam",
        "rtsp://user:password@example/stream",
        5,
        capture_factory=lambda _: capture,
        clock=lambda: "2026-08-14T00:00:00Z",
    )
    frame = next(source.read_frames())
    assert (frame.frame_id, frame.captured_at, frame.source_type) == (1, "2026-08-14T00:00:00Z", "RTSP")
    source.release()
    source.release()
    assert capture.released


def test_rtsp_credentials_are_redacted():
    assert redact_rtsp_uri("rtsp://user:password@192.168.1.1/live") == "rtsp://user:***@192.168.1.1/live"


def test_stop_interrupts_reconnect_backoff():
    stopped = threading.Event()
    stopped.set()
    source = RTSPVideoSource(
        "cam", "rtsp://offline", 5, capture_factory=lambda _: FakeCapture(opened=False), stop_event=stopped
    )
    assert list(source.read_frames()) == []


def test_external_stop_interrupts_active_reconnect_backoff():
    stopped = threading.Event()
    source = RTSPVideoSource(
        "cam",
        "rtsp://offline",
        5,
        {"reconnect": {"initial_backoff_s": 5.0}},
        capture_factory=lambda: FakeCapture(opened=False),
    )
    source.configure_stop(stopped, None)
    thread = threading.Thread(target=lambda: list(source.read_frames()))
    thread.start()
    time.sleep(0.05)
    started = time.monotonic()
    stopped.set()
    thread.join(timeout=0.5)
    assert not thread.is_alive()
    assert time.monotonic() - started < 0.5


def test_initial_failures_then_success_and_midstream_reconnect():
    frame = np.zeros((2, 2, 3))
    captures = CaptureFactory(
        [
            FakeCapture(opened=False),
            FakeCapture([(True, frame), (False, None)]),
            FakeCapture([(True, frame)]),
        ]
    )
    source = RTSPVideoSource(
        "cam",
        "rtsp://example/live",
        5,
        {"reconnect": {"initial_backoff_s": 0.0}},
        capture_factory=captures,
    )
    frames = source.read_frames()
    first = next(frames)
    second = next(frames)
    source.release()
    assert (first.frame_id, second.frame_id) == (1, 2)
    assert source.session_id == 2
    assert source.reconnect_count == 2
    assert source.read_decode_errors == 1


def test_wall_clock_is_clamped_when_clock_moves_backwards_across_reconnect():
    frame = np.zeros((2, 2, 3))
    clocks = iter(["2026-08-14T00:00:01Z", "2026-08-14T00:00:00Z"])
    captures = CaptureFactory(
        [
            FakeCapture([(True, frame), (False, None)]),
            FakeCapture([(True, frame)]),
        ]
    )
    source = RTSPVideoSource(
        "cam",
        "rtsp://example/live",
        5,
        {"reconnect": {"initial_backoff_s": 0.0}},
        capture_factory=captures,
        clock=lambda: next(clocks),
    )
    frames = source.read_frames()
    first, second = next(frames), next(frames)
    source.release()
    assert parse_iso_timestamp(second.captured_at) == parse_iso_timestamp(first.captured_at)


def test_reconnect_can_be_disabled_without_busy_loop():
    factory = CaptureFactory([FakeCapture(opened=False)])
    source = RTSPVideoSource(
        "cam",
        "rtsp://offline",
        5,
        {"reconnect": {"enabled": False}},
        capture_factory=factory,
    )
    assert list(source.read_frames()) == []
    assert factory.calls == 1


def test_exponential_backoff_is_capped():
    waits = []
    source = RTSPVideoSource(
        "cam",
        "rtsp://offline",
        5,
        {
            "reconnect": {
                "initial_backoff_s": 1.0,
                "max_backoff_s": 4.0,
                "multiplier": 2.0,
            }
        },
        capture_factory=lambda: FakeCapture(opened=False),
    )

    def record_wait(delay_s):
        waits.append(delay_s)
        if len(waits) == 4:
            source.release()

    source._wait = record_wait
    assert list(source.read_frames()) == []
    assert waits == [1.0, 2.0, 4.0, 4.0]


def test_default_opencv_open_receives_timeout_parameters(monkeypatch):
    capture = FakeCapture(opened=False)
    opened_with = []

    def open_capture(uri, backend, params):
        opened_with.append((uri, backend, params))
        capture.opened = True
        return True

    capture.open = open_capture
    monkeypatch.setattr(cv2, "VideoCapture", lambda: capture)
    source = RTSPVideoSource(
        "cam",
        "rtsp://example/live",
        5,
        {"rtsp": {"open_timeout_ms": 1234, "read_timeout_ms": 2345}},
    )
    assert source._open()
    source.release()
    assert opened_with[0][2] == [
        cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,
        1234,
        cv2.CAP_PROP_READ_TIMEOUT_MSEC,
        2345,
    ]


def test_long_outage_callback_fires_before_reconnect():
    observed = []
    source = RTSPVideoSource("cam", "rtsp://offline", 5)
    source.configure_outage_handler(0.0, observed.append)
    source._outage_started = time.monotonic() - 1.0
    source._wait(0.01)
    assert observed and observed[0] >= 1.0


def test_latest_frame_reader_keeps_one_slot_and_reports_latest_sequence():
    frame = np.zeros((2, 2, 3))
    capture = FakeCapture([(True, frame) for _ in range(10)])
    reader = LatestFrameReader(capture, lambda: "2026-08-14T00:00:00Z")
    reader.start()
    deadline = time.monotonic() + 0.5
    while not reader._failed and time.monotonic() < deadline:
        time.sleep(0.001)
    latest = reader.next_frame(0, lambda: False)
    reader.stop()
    assert latest is not None
    assert latest[0] == 10
