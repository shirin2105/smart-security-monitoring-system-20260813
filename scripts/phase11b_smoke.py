"""Run exactly one real frame through the Phase 11B pipeline with stage markers."""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.cv.detector import DEIMv2Detector
from app.cv.events.phase7c_abandoned_adapter import Phase7CAbandonedAdapter
from app.cv.frame_sampler import FrameSampler
from app.cv.track_store import TrackStore
from app.cv.tracker import ByteTrackMultiObjectTracker
from app.sources.mp4_source import MP4VideoSource


def mark(stage: str) -> None:
    print(f"PHASE11B_STAGE={stage}", file=sys.stderr, flush=True)


def main() -> int:
    clip_name = os.getenv("PHASE11_CLIP_NAME", "LeftBag")
    clip = Path("phase8_dataset/videos") / f"{clip_name}.mpg"
    log_path = Path("artifacts/phase11b") / f"{clip_name}-smoke-error.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        mark("CUDA_CHECK")
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available")
        mark("CHECKPOINT_LOAD")
        detector = DEIMv2Detector(**settings.detector_config)
        mark("SOURCE_OPEN")
        source = MP4VideoSource(clip_name, str(clip), "FILE", inference_fps=5.0)
        if source.cap is None or not source.cap.isOpened():
            raise RuntimeError(f"video source failed to open for clip {clip_name!r}")
        tracker = ByteTrackMultiObjectTracker(clip_name, frame_rate=5.0)
        store = TrackStore(clip_name)
        cfg = dict(settings.event_rules["abandoned_object"]["phase7c"])
        cfg["debug"] = {"enabled": True, "emit_trace_jsonl": True, "trace_output_dir": "artifacts/phase11b/traces"}
        adapter = Phase7CAbandonedAdapter(clip_name, cfg, fps_hint=5.0)
        sampler = FrameSampler(5.0)
        trace_path = Path("artifacts/phase11b/traces") / f"{clip_name}.jsonl"
        first_processed = True
        for frame in source.read_frames():
            if not sampler.should_process(frame):
                continue
            if first_processed:
                mark("FRAME_READ")
                mark("DETECTOR_CALL")
            detections, _ = detector.detect(frame)
            if first_processed:
                mark("TRACKER_UPDATE")
            tracks = tracker.track(detections, frame)
            active = [store.update_track(track) for track in tracks]
            if first_processed:
                mark("PHASE7C_ADAPTER")
                first_processed = False
            adapter.evaluate(active, frame)
            if trace_path.exists() and trace_path.stat().st_size > 0:
                mark("TRACE_WRITTEN")
                break
        else:
            raise RuntimeError("clip ended before a Phase7C trace row was written")
        source.release()
        return 0
    except BaseException:
        trace = traceback.format_exc()
        print(trace, file=sys.stderr, flush=True)
        log_path.write_text(trace, encoding="utf-8")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
