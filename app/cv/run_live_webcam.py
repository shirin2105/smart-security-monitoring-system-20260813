"""Run live real-time AI detection on Camera 3 webcam stream.

Connects to the MJPEG stream at http://localhost:8081/cameras/3/stream as an HTTP client,
maintains a rolling 20-second video frame buffer in memory, runs DEIMv2 inference at 5 FPS,
and when an event occurs, captures [+3s] post-event frames, encodes the true [now-20s, now+3s]
video clip with ffmpeg (H.264 / yuv420p), and posts the alert to the backend.
"""

from __future__ import annotations

import argparse
import collections
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cv2
import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.config import settings
from app.common.schemas import FrameData
from app.cv.detector import DEIMv2Detector
from app.cv.tracker import ByteTrackMultiObjectTracker
from app.cv.track_store import TrackStore
from app.cv.events.phase7c_abandoned_adapter import Phase7CAbandonedAdapter
import yaml

CLIP_BEFORE_S = 20.0
CLIP_AFTER_S = 3.0
INFERENCE_FPS = 5.0
MAX_BUFFER_FRAMES = int((CLIP_BEFORE_S + CLIP_AFTER_S + 2.0) * INFERENCE_FPS)  # ~125 frames

_CANDIDATE_ID_SAFE = re.compile(r"[^A-Za-z0-9._-]")


def _safe_candidate_id(raw: str) -> str:
    sanitized = _CANDIDATE_ID_SAFE.sub("_", raw)
    if not sanitized or not sanitized[0].isalnum():
        sanitized = f"cv-{sanitized}" if sanitized else f"cv-{abs(hash(raw))}"
    return sanitized[:255]


def save_frames_to_mp4(
    frames: list[tuple[float, Any]],
    out_path: Path,
    fps: float = 5.0,
    ffmpeg_bin: str = "ffmpeg",
) -> bool:
    """Encode an in-memory sequence of OpenCV BGR frames to a web-compatible H.264 MP4."""
    if not frames:
        return False
    out_path.parent.mkdir(parents=True, exist_ok=True)
    height, width = frames[0][1].shape[:2]

    # Use ffmpeg stdin pipe for reliable browser-compatible libx264 yuv420p encoding
    cmd = [
        ffmpeg_bin,
        "-y",
        "-f",
        "rawvideo",
        "-vcodec",
        "rawvideo",
        "-s",
        f"{width}x{height}",
        "-pix_fmt",
        "bgr24",
        "-r",
        f"{fps:.2f}",
        "-i",
        "-",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "veryfast",
        "-an",
        str(out_path),
    ]
    try:
        raw_bytes = b"".join(frame.tobytes() for _, frame in frames)
        proc = subprocess.run(cmd, input=raw_bytes, capture_output=True, timeout=15)
        if proc.returncode == 0 and out_path.exists() and out_path.stat().st_size > 1024:
            return True
        print(f"[LiveWebcamCV] ffmpeg failed: {proc.stderr.decode('utf-8', errors='ignore')}", flush=True)
    except Exception as exc:
        print(f"[LiveWebcamCV] ffmpeg encode exception for {out_path}: {exc}", flush=True)

    # Fallback to OpenCV VideoWriter if ffmpeg fails
    try:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(out_path), fourcc, fps, (width, height))
        for _, frame in frames:
            writer.write(frame)
        writer.release()
        return out_path.exists() and out_path.stat().st_size > 1024
    except Exception as exc:
        print(f"[LiveWebcamCV] VideoWriter fallback failed: {exc}", flush=True)
        return False


def run_live_webcam_cv(
    stream_url: str = "http://localhost:8081/cameras/3/stream",
    camera_id: str = "cam_03",
    backend_url: str = "http://127.0.0.1:8000",
    token: str | None = None,
    evidence_dir: str | os.PathLike[str] = REPO_ROOT / "artifacts" / "evidence_clips",
    debounce_seconds: float = 20.0,
) -> int:
    token = token or os.getenv("EVENT_INGEST_TOKEN", "")
    if not token.strip():
        print("[LiveWebcamCV] EVENT_INGEST_TOKEN is required to publish alerts")
        return 2

    evidence_dir = Path(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    print(f"[LiveWebcamCV] Initializing DEIMv2 detector on GPU...", flush=True)
    detector = DEIMv2Detector(**settings.detector_config)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    ingest_url = f"{backend_url.rstrip('/')}/api/v1/events/ingest"

    print(f"[LiveWebcamCV] Connecting to live stream at {stream_url}...", flush=True)
    cap = cv2.VideoCapture(stream_url)
    if not cap.isOpened():
        print(f"[LiveWebcamCV] Failed to open stream {stream_url}", flush=True)
        return 1

    print(f"[LiveWebcamCV] Connected. Monitoring Camera 3 for real-time events...", flush=True)

    # Load event rules config
    rules_cfg = {}
    rules_path = REPO_ROOT / "configs" / "event_rules.yaml"
    if rules_path.exists():
        try:
            with open(rules_path, "r", encoding="utf-8") as f:
                rules_cfg = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"[LiveWebcamCV] Warning: could not load event_rules.yaml: {e}", flush=True)

    abandoned_cfg = (rules_cfg.get("abandoned_object") or {}).get("phase7c") or {}
    abandoned_adapter = Phase7CAbandonedAdapter(camera_id, config=abandoned_cfg, fps_hint=INFERENCE_FPS)
    tracker = ByteTrackMultiObjectTracker(camera_id, frame_rate=INFERENCE_FPS)
    track_store = TrackStore(camera_id)

    frame_buffer: collections.deque[tuple[float, Any]] = collections.deque(maxlen=MAX_BUFFER_FRAMES)
    last_crowd_alert_time = 0.0
    last_abandoned_alert_time = 0.0
    last_frame_time = time.time()
    frame_interval = 1.0 / INFERENCE_FPS

    pending_events: list[dict[str, Any]] = []

    try:
        while True:
            ret, frame = cap.read()
            now = time.time()
            if not ret or frame is None:
                time.sleep(0.05)
                continue

            frame_buffer.append((now, frame.copy()))

            # Throttle inference to 5 FPS
            if (now - last_frame_time) < frame_interval:
                continue
            last_frame_time = now

            # Check if any pending events need their post-event frames finished
            for pending in list(pending_events):
                if now >= pending["capture_until"]:
                    pending_events.remove(pending)
                    # Cut the exact [-20s, +3s] video from frame_buffer
                    clip_start = pending["detected_at_time"] - CLIP_BEFORE_S
                    clip_end = pending["detected_at_time"] + CLIP_AFTER_S
                    clip_frames = [
                        (t, f) for (t, f) in frame_buffer
                        if clip_start <= t <= clip_end
                    ]
                    if not clip_frames:
                        clip_frames = list(frame_buffer)
                    clip_name = f"{pending['candidate_id']}.mp4"
                    out_path = evidence_dir / clip_name
                    if save_frames_to_mp4(clip_frames, out_path, fps=INFERENCE_FPS):
                        print(f"[LiveWebcamCV] Cut real 23s evidence clip: {clip_name} ({len(clip_frames)} frames)", flush=True)
                        # Backfill artifact
                        try:
                            with httpx.Client(timeout=10.0) as client:
                                client.post(
                                    f"{backend_url.rstrip('/')}/api/v1/events/{pending['incident_id']}/artifact-ready",
                                    json={"uri": f"/evidence/{clip_name}", "redactionStatus": "COMPLETE"},
                                    headers=headers,
                                )
                                print(f"[LiveWebcamCV] Backfilled video artifact to incident #{pending['incident_id']}", flush=True)
                        except Exception as exc:
                            print(f"[LiveWebcamCV] Failed to backfill artifact: {exc}", flush=True)

            # Run detection
            try:
                frame_data = FrameData(
                    camera_id=camera_id,
                    frame_id=int(now * 1000) % 1000000,
                    captured_at=datetime.now(UTC).isoformat(),
                    source_type="LIVE",
                    source_fps=15.0,
                    inference_fps=INFERENCE_FPS,
                    image=frame,
                )
                detections, _ = detector.detect(frame_data)
            except Exception as e:
                print(f"[LiveWebcamCV] Detection error: {e}", flush=True)
                continue

            persons = [d for d in detections if d.class_name == "person" and d.confidence >= 0.40]
            luggages = [d for d in detections if d.class_name == "luggage" and d.confidence >= 0.35]

            # 1. Event: CROWD_THRESHOLD (Đám đông)
            if len(persons) >= 2 and (now - last_crowd_alert_time) > debounce_seconds:
                last_crowd_alert_time = now
                detected_at_iso = datetime.now(UTC).isoformat()
                candidate_id = _safe_candidate_id(f"cam_03_crowd_{uuid.uuid4().hex[:8]}")

                payload = {
                    "candidateId": candidate_id,
                    "sourceEngine": "CV",
                    "cameraId": camera_id,
                    "sourceType": "LIVE",
                    "eventType": "CROWD_THRESHOLD",
                    "eventDetected": True,
                    "detectedAt": detected_at_iso,
                    "firstSeenAt": detected_at_iso,
                    "lastSeenAt": detected_at_iso,
                    "confidence": float(max(p.confidence for p in persons)),
                    "trackCount": len(persons),
                    "trackIds": [],
                    "observations": {"personCount": len(persons), "insideZone": True},
                    "modelVersion": "deimv2-phase7a",
                    "ruleVersion": "crowd-rule-v1",
                    "policyVersion": 1,
                    "artifact": {
                        "available": False,
                        "contentType": "video/mp4",
                        "redactionStatus": "PENDING",
                        "uri": None,
                    },
                }

                print(f"[LiveWebcamCV] [ALERT] CROWD DETECTED: {len(persons)} persons! Emitting candidateId={candidate_id}...", flush=True)
                try:
                    with httpx.Client(timeout=5.0) as client:
                        resp = client.post(
                            ingest_url,
                            json=payload,
                            headers={**headers, "Idempotency-Key": candidate_id},
                        )
                        if 200 <= resp.status_code < 300:
                            data = resp.json()
                            inc_id = (data.get("incident") or {}).get("id")
                            print(f"[LiveWebcamCV] Published CROWD incident #{inc_id}", flush=True)
                            if inc_id is not None:
                                pending_events.append({
                                    "incident_id": inc_id,
                                    "candidate_id": candidate_id,
                                    "detected_at_time": now,
                                    "capture_until": now + CLIP_AFTER_S,
                                })
                except Exception as exc:
                    print(f"[LiveWebcamCV] Ingest crowd failed: {exc}", flush=True)

            # 2. Event: ABANDONED_OBJECT (Quên đồ) via Phase7C Tracking
            try:
                track_results = tracker.track(detections, frame_data)
                active_tracks = [track_store.update_track(tr) for tr in track_results]
                signals = abandoned_adapter.evaluate(active_tracks, frame_data)
                for sig in signals:
                    if sig.event_type == "ABANDONED_OBJECT" and sig.active and (now - last_abandoned_alert_time) > debounce_seconds:
                        last_abandoned_alert_time = now
                        detected_at_iso = datetime.now(UTC).isoformat()
                        candidate_id = _safe_candidate_id(f"cam_03_abandoned_{uuid.uuid4().hex[:8]}")

                        evidence = sig.evidence or {}
                        payload = {
                            "candidateId": candidate_id,
                            "sourceEngine": "CV",
                            "cameraId": camera_id,
                            "sourceType": "LIVE",
                            "eventType": "ABANDONED_OBJECT",
                            "eventDetected": True,
                            "detectedAt": detected_at_iso,
                            "firstSeenAt": detected_at_iso,
                            "lastSeenAt": detected_at_iso,
                            "confidence": float(sig.cv_confidence),
                            "trackCount": len(track_results),
                            "trackIds": [],
                            "observations": {
                                "personCount": len(persons),
                                "stationarySeconds": float(evidence.get("stationary_duration_s", 0.0)),
                                "ownerAbsentSeconds": float(evidence.get("owner_away_duration_s", 0.0)),
                            },
                            "modelVersion": "deimv2-phase7c",
                            "ruleVersion": "abandoned-rule-v2",
                            "policyVersion": 2,
                            "artifact": {
                                "available": False,
                                "contentType": "video/mp4",
                                "redactionStatus": "PENDING",
                                "uri": None,
                            },
                        }

                        print(f"[LiveWebcamCV] [ALERT] ABANDONED OBJECT DETECTED: key={sig.entity_key}! Emitting candidateId={candidate_id}...", flush=True)
                        try:
                            with httpx.Client(timeout=5.0) as client:
                                resp = client.post(
                                    ingest_url,
                                    json=payload,
                                    headers={**headers, "Idempotency-Key": candidate_id},
                                )
                                if 200 <= resp.status_code < 300:
                                    data = resp.json()
                                    inc_id = (data.get("incident") or {}).get("id")
                                    print(f"[LiveWebcamCV] Published ABANDONED incident #{inc_id}", flush=True)
                                    if inc_id is not None:
                                        pending_events.append({
                                            "incident_id": inc_id,
                                            "candidate_id": candidate_id,
                                            "detected_at_time": now,
                                            "capture_until": now + CLIP_AFTER_S,
                                        })
                        except Exception as exc:
                            print(f"[LiveWebcamCV] Ingest abandoned failed: {exc}", flush=True)
            except Exception as exc:
                print(f"[LiveWebcamCV] Tracking/Abandoned error: {exc}", flush=True)

    except KeyboardInterrupt:
        print("[LiveWebcamCV] Stopped by user", flush=True)
    finally:
        cap.release()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run real-time CV detection on Camera 3 Webcam stream")
    parser.add_argument("--stream-url", default="http://localhost:8081/cameras/3/stream")
    parser.add_argument("--camera-id", default="cam_03")
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000")
    parser.add_argument("--token", default=None)
    parser.add_argument("--evidence-dir", default=str(REPO_ROOT / "artifacts" / "evidence_clips"))
    parser.add_argument("--debounce", type=float, default=20.0, help="Debounce seconds between alerts")
    args = parser.parse_args()

    return run_live_webcam_cv(
        stream_url=args.stream_url,
        camera_id=args.camera_id,
        backend_url=args.backend_url,
        token=args.token,
        evidence_dir=args.evidence_dir,
        debounce_seconds=args.debounce,
    )


if __name__ == "__main__":
    sys.exit(main())
