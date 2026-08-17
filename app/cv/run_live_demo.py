"""Run the real DEIMv2 model LIVE over the demo clip and emit alerts + evidence clips.

This replaces the prerendered/scripted frontend alert: the unified CV runtime
processes the clip frame-by-frame, and every START detection is published as a
real backend incident (``EventCandidateIn``) with a video-timeline ``detectedAt``
and a standalone ffmpeg-cut evidence clip (``[detectedAt-20s, detectedAt+3s]``)
served at ``/evidence``.

The camera feed loops in the browser, so the model replays the clip in a loop
too (``--loops 0`` runs forever): every pass gets a fresh run id -> new candidate
ids -> a new alert on the web, exactly like a camera that keeps getting watched.

Usage:
    $env:EVENT_INGEST_TOKEN = '<same-secret-as-backend>'
    python -m app.cv.run_live_demo --loops 0
"""

from __future__ import annotations

import argparse
import os
import time
import uuid
from pathlib import Path

from app.config import settings
from app.cv.clip_publisher import EvidenceClipPublisher
from app.cv.detector import DEIMv2Detector
from app.cv.events.frame_time import frame_time_seconds
from app.cv.worker import CVWorker
from app.sources.mp4_source import MP4VideoSource

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CLIP = (
    REPO_ROOT / "front-end" / "public" / "videos" / "camera-1-aboda-tracking.h264.mp4"
)


class PacedVideoSource:
    """Proxy a video source and pace each frame to wall-clock real time (1x).

    Keeps the model's playhead at ``(now - epoch) % duration`` — the same live
    position the browser derives — so a detection is returned at the exact moment
    the user is watching it, never pre-created ahead of playback.
    """

    def __init__(self, source, epoch_wall: float):
        self._source = source
        self._epoch = epoch_wall

    def read_frames(self):
        for frame in self._source.read_frames():
            now_s = frame_time_seconds(frame)
            remaining = (self._epoch + now_s) - time.time()
            if remaining > 0:
                time.sleep(remaining)
            yield frame

    def __getattr__(self, name):
        return getattr(self._source, name)


def run_live_demo(
    clip: str | os.PathLike[str] = DEFAULT_CLIP,
    camera_id: str = "cam_01",
    backend_url: str = "http://127.0.0.1:8000",
    token: str | None = None,
    evidence_dir: str | os.PathLike[str] = REPO_ROOT / "artifacts" / "evidence_clips",
    enabled_event_types: set[str] | None = None,
    loops: int = 0,
    loop_delay_s: float = 0.0,
) -> int:
    clip = Path(clip)
    if not clip.exists():
        print(f"[run_live_demo] Demo clip not found: {clip}")
        return 2

    token = token or os.getenv("EVENT_INGEST_TOKEN", "")
    if not token.strip():
        print("[run_live_demo] EVENT_INGEST_TOKEN is required to publish alerts")
        return 2

    # Model nạp MỘT lần và dùng chung cho mọi pass — giống camera thật.
    detector = DEIMv2Detector(**settings.detector_config)
    publisher = EvidenceClipPublisher(
        source_clip=clip,
        endpoint_url=f"{backend_url.rstrip('/')}/api/v1/events/ingest",
        bearer_token=token,
        evidence_dir=evidence_dir,
        enabled_event_types=enabled_event_types,
    )

    pass_no = 0
    total_starts = 0
    while loops == 0 or pass_no < loops:
        pass_no += 1
        # Mỗi pass một run_id mới -> event/candidate id mới -> alert mới trên web.
        run_id = uuid.uuid4().hex[:8]
        # Đồng hồ wall-clock của vòng lặp này — web dùng nó để đồng bộ playhead.
        epoch_wall = time.time()
        source = MP4VideoSource(camera_id, str(clip), source_type="MP4", inference_fps=5.0)
        source = PacedVideoSource(source, epoch_wall)
        publisher.post_stream_clock(camera_id, epoch_wall)
        worker = CVWorker(
            camera_id=camera_id,
            source=source,
            publisher=publisher,
            detector=detector,
            candidate_id_namespace=lambda value: f"{run_id}:{value}",
        )
        print(
            f"[run_live_demo] Pass {pass_no} over {clip} (run_id={run_id}, epoch={epoch_wall:.3f})",
            flush=True,
        )
        events = worker.run()
        starts = [e for e in events if e.event_state == "START"]
        total_starts += len(starts)
        print(
            f"[run_live_demo] Pass {pass_no} done: {len(events)} CVEvents, "
            f"{len(starts)} START detections.",
            flush=True,
        )
        if loops and pass_no >= loops:
            break
        if loop_delay_s > 0:
            time.sleep(loop_delay_s)
    print(f"[run_live_demo] Finished. {pass_no} passes, {total_starts} total START detections.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run live CV over the demo clip and emit alerts")
    parser.add_argument("--clip", default=str(DEFAULT_CLIP), help="Path to the source video")
    parser.add_argument("--camera-id", default="cam_01")
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000")
    parser.add_argument("--token", default=None, help="EVENT_INGEST_TOKEN (else $EVENT_INGEST_TOKEN)")
    parser.add_argument("--evidence-dir", default=str(REPO_ROOT / "artifacts" / "evidence_clips"))
    parser.add_argument(
        "--enabled-event-types",
        default="ABANDONED_OBJECT",
        help="Comma-separated event types to publish (empty = all). Default only ABANDONED_OBJECT.",
    )
    parser.add_argument(
        "--loops",
        type=int,
        default=0,
        help="Number of replay passes (0 = run forever, matching the looping camera feed)",
    )
    parser.add_argument("--loop-delay", type=float, default=0.0, help="Seconds to pause between passes")
    args = parser.parse_args()
    enabled = (
        {name.strip() for name in args.enabled_event_types.split(",") if name.strip()}
        if args.enabled_event_types.strip()
        else None
    )
    return run_live_demo(
        clip=args.clip,
        camera_id=args.camera_id,
        backend_url=args.backend_url,
        token=args.token,
        evidence_dir=args.evidence_dir,
        enabled_event_types=enabled,
        loops=args.loops,
        loop_delay_s=args.loop_delay,
    )


if __name__ == "__main__":
    raise SystemExit(main())
