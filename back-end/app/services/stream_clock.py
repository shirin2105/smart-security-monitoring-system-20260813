"""Per-camera live-stream clock shared between the CV producer and the frontend.

The CV demo replays the source video in a loop paced to wall-clock. Each pass it
registers ``epoch`` (wall-clock when the loop restarted) and ``duration`` (source
seconds). The frontend then positions every camera video surface at the same
playhead ``(now - epoch) % duration``, so tiles/modal stay in phase with what the
model is watching — a real continuous camera stream instead of per-element
replays from t=0.
"""

_clock: dict[int, dict[str, float]] = {}


def set_stream_clock(camera_id: int, epoch: float, duration: float) -> None:
    _clock[camera_id] = {"epoch": epoch, "duration": duration}


def get_stream_clocks() -> list[dict]:
    return [
        {"camera_id": camera_id, **entry}
        for camera_id, entry in _clock.items()
    ]