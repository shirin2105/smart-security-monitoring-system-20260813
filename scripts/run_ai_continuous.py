import os
import sys
import time
import uuid
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.config import settings
from app.cv.clip_publisher import EvidenceClipPublisher
from app.cv.detector import DEIMv2Detector
from app.cv.events.frame_time import frame_time_seconds
from app.cv.multi_camera_runner import MultiCameraRunner
from app.cv.worker import CVWorker
from app.sources.mp4_source import MP4VideoSource

TOKEN = os.getenv("EVENT_INGEST_TOKEN", "dev-secret-token-2026")
BACKEND_URL = os.getenv("EVENT_INGEST_URL", "http://127.0.0.1:8000/api/v1/events/ingest")
EVIDENCE_DIR = ROOT_DIR / "artifacts" / "evidence_clips"


class PacedVideoSource:
    """Proxy a video source and pace each frame to wall-clock real time (1x).

    Keeps the model's playhead at (now - epoch) % duration — the same live
    position the browser derives — so detections are returned at the exact moment
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


def main():
    print("=" * 60, flush=True)
    print("AI CV Runner (Real DEIMv2 Inference + Real-Time Video Sync)", flush=True)
    print(f"Cameras: {[c.get('camera_id') for c in settings.cameras if c.get('enabled', True)]}", flush=True)
    print(f"Ingest URL: {BACKEND_URL}", flush=True)
    print("=" * 60, flush=True)

    print("Loading DEIMv2 model and weights...", flush=True)
    model_cfg = settings.detector_config
    shared_detector = DEIMv2Detector(**model_cfg)
    print("DEIMv2 model ready!", flush=True)

    loop_count = 0
    while True:
        loop_count += 1
        run_id = uuid.uuid4().hex[:8]
        epoch_wall = time.time()
        print(f"\n[AI-LOOP #{loop_count} | run_id={run_id} | epoch={epoch_wall:.3f}] Processing 3 synchronized camera feeds...", flush=True)

        def worker_factory(camera_id, source_uri=None, **kwargs):
            clip_path = source_uri or "./tests/clips/walking_people.mp4"
            publisher = EvidenceClipPublisher(
                source_clip=clip_path,
                endpoint_url=BACKEND_URL,
                bearer_token=TOKEN,
                evidence_dir=EVIDENCE_DIR,
            )
            publisher.post_stream_clock(camera_id, epoch_wall)
            source = MP4VideoSource(camera_id, str(clip_path), source_type="MP4", inference_fps=5.0)
            paced_source = PacedVideoSource(source, epoch_wall)
            return CVWorker(
                camera_id=camera_id,
                source=paced_source,
                publisher=publisher,
                candidate_id_namespace=lambda cid: f"live-{run_id}-{cid}",
                **kwargs,
            )

        runner = MultiCameraRunner(detector=shared_detector, worker_factory=worker_factory)
        try:
            results = runner.run()
            for cam_id, res in results.items():
                status = res.get("status")
                events = res.get("events", [])
                print(f"  Camera [{cam_id}]: status={status}, detected_events={len(events)}", flush=True)
        except Exception as e:
            print(f"  Error in CV loop: {e}", flush=True)

        time.sleep(1)


if __name__ == "__main__":
    main()

