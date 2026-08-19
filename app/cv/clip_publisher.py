"""Publish CV detections as real-time backend alerts with a cut evidence video.

Replaces the prerendered/scripted alert path: while the model runs LIVE over a
video file, every START detection is converted into a schema-valid
``EventCandidateIn`` (video-timeline ``detectedAt``), a standalone evidence clip
is cut with ffmpeg from ``[detectedAt-20s, detectedAt+3s]`` and posted to the
backend ingest endpoint so the frontend receives a real ``NEW_ALERT``.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from app.cv.contracts.cv_event import CVEvent
from app.publisher.base import CVEventPublisher
from app.sources.mp4_source import DEFAULT_FILE_SOURCE_EPOCH

CLIP_BEFORE_S = 20.0
CLIP_AFTER_S = 3.0

_CANDIDATE_ID_SAFE = re.compile(r"[^A-Za-z0-9._-]")


def _safe_candidate_id(raw: str) -> str:
    sanitized = _CANDIDATE_ID_SAFE.sub("_", raw)
    if not sanitized or not sanitized[0].isalnum():
        sanitized = f"cv-{sanitized}" if sanitized else f"cv-{abs(hash(raw))}"
    return sanitized[:255]


def _video_epoch() -> datetime:
    return datetime.fromisoformat(DEFAULT_FILE_SOURCE_EPOCH)


def clip_window(detected_at_s: float, duration_s: float | None) -> tuple[float, float]:
    """Return (start_s, end_s) clamped to [0, duration] for the evidence clip."""
    start = max(0.0, detected_at_s - CLIP_BEFORE_S)
    end = detected_at_s + CLIP_AFTER_S
    if duration_s is not None and end > duration_s:
        end = duration_s
    return start, max(start, end)


def extract_evidence_clip(
    src: str | os.PathLike[str],
    out_path: str | os.PathLike[str],
    detected_at_s: float,
    duration_s: float | None = None,
    ffmpeg_bin: str = "ffmpeg",
) -> bool:
    """Cut a standalone mp4 from ``[detectedAt-20s, detectedAt+3s]`` of ``src``.

    Returns True when ffmpeg produced the output file.
    """
    start, end = clip_window(detected_at_s, duration_s)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        return True
    cmd = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(src),
        "-ss",
        f"{start:.3f}",
        "-to",
        f"{end:.3f}",
        "-c:v",
        "libx264",
        "-an",
        "-preset",
        "veryfast",
        str(out_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"[EvidenceClip] ffmpeg failed for {out_path}: {exc}")
        return False
    return out_path.exists()


def probe_duration(src: str | os.PathLike[str]) -> float | None:
    """Best-effort clip duration via ffmpeg; None when unavailable."""
    cmd = ["ffmpeg", "-i", str(src)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        return None
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", proc.stderr)
    if not match:
        return None
    h, m, s = (int(match.group(1)), int(match.group(2)), float(match.group(3)))
    return h * 3600 + m * 60 + s


def build_event_candidate(
    event: CVEvent,
    detected_at_s: float,
    clip_url: str | None = None,
) -> dict[str, Any]:
    """Map a cv-event-v1 START record to the backend EventCandidateIn contract.

    ``clip_url=None`` marks the artifact PENDING (alert posted immediately, video
    backfilled later via ``mark_artifact_ready`` once the clip is cut).
    """
    now_ts = datetime.now(UTC).isoformat()
    objects = event.objects or {}
    person_count = int(objects.get("personCount", objects.get("person", 0)) or 0)
    return {
        "candidateId": _safe_candidate_id(event.event_id),
        "sourceEngine": "CV",
        "cameraId": event.camera_id,
        "sourceType": "SIMULATED",
        "eventType": event.event_type,
        "eventDetected": True,
        "detectedAt": now_ts,
        "firstSeenAt": now_ts,
        "lastSeenAt": now_ts,
        "confidence": float(event.cv_confidence),
        "trackCount": 1,
        "trackIds": [],
        "observations": {"personCount": person_count},
        "modelVersion": "deimv2-phase7a",
        "ruleVersion": "intrusion-rule-v1",
        "policyVersion": 1,
        "artifact": {
            "available": clip_url is not None,
            "contentType": "video/mp4",
            "redactionStatus": "COMPLETE" if clip_url is not None else "PENDING",
            "uri": clip_url,
        },
    }


class EvidenceClipPublisher(CVEventPublisher):
    """CVEvent publisher that emits real backend alerts with cut evidence clips."""

    def __init__(
        self,
        source_clip: str | os.PathLike[str],
        endpoint_url: str = "http://127.0.0.1:8000/api/v1/events/ingest",
        bearer_token: str = "",
        evidence_dir: str | os.PathLike[str] = "artifacts/evidence_clips",
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
        enabled_event_types: set[str] | None = None,
    ):
        self.source_clip = str(source_clip)
        self.endpoint_url = endpoint_url
        self.bearer_token = bearer_token
        self.evidence_dir = Path(evidence_dir)
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.enabled_event_types = enabled_event_types
        self._duration = probe_duration(self.source_clip)

    def publish(self, event: CVEvent) -> bool:
        if event.event_state != "START":
            # UPDATE/END extend the same lifecycle; do not re-post (keeps idempotency).
            return True
        if self.enabled_event_types is not None and event.event_type not in self.enabled_event_types:
            # Loại cảnh báo không được phép (vd: ZONE_INTRUSION) — bỏ qua, không cắt clip.
            return True
        detected_at_s = float(event.event_time_s)
        clip_name = f"{_safe_candidate_id(event.event_id)}.mp4"
        out_path = self.evidence_dir / clip_name

        # 1) Đăng thông báo NGAY khi phát hiện — artifact PENDING, video chưa sẵn sàng.
        pending = build_event_candidate(event, detected_at_s, clip_url=None)
        incident_id = self._post(pending)
        if incident_id is None:
            return False

        # 2) Cắt clip bằng chứng sau đó.
        if not extract_evidence_clip(self.source_clip, out_path, detected_at_s, self._duration):
            return False

        # 3) Bổ sung video đã cắt vào sự cố đã hiển thị.
        clip_url = f"/evidence/{clip_name}"
        return self._mark_artifact_ready(incident_id, clip_url)

    def _post(self, payload: dict[str, Any]) -> int | None:
        """POST an event candidate; return the backend incident id when accepted."""
        if not self.bearer_token.strip():
            print("[EvidenceClip] Refused unauthenticated publish (set EVENT_INGEST_TOKEN)")
            return None
        headers = {
            "Content-Type": "application/json",
            "Idempotency-Key": payload["candidateId"],
            "Authorization": f"Bearer {self.bearer_token}",
        }
        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(self.endpoint_url, json=payload, headers=headers)
                if 200 <= response.status_code < 300:
                    print(f"[EvidenceClip] Published candidateId={payload['candidateId']} -> {response.status_code}", flush=True)
                    try:
                        incident = response.json().get("incident") or {}
                        incident_id = incident.get("id")
                        if isinstance(incident_id, int):
                            return incident_id
                    except ValueError:
                        pass
                    return None
                if response.status_code not in (408, 429) and response.status_code < 500:
                    print(f"[EvidenceClip] Permanent failure candidateId={payload['candidateId']}: {response.status_code}", flush=True)
                    return None
                print(f"[EvidenceClip] Attempt {attempt}/{self.max_retries} HTTP {response.status_code}", flush=True)
            except httpx.TransportError as exc:
                print(f"[EvidenceClip] Attempt {attempt}/{self.max_retries} error: {type(exc).__name__}", flush=True)
            if attempt < self.max_retries:
                time.sleep(0.2 * (2 ** (attempt - 1)))
        return None

    def post_stream_clock(self, camera_id: str, epoch: float) -> bool:
        """Register the live-loop wall-clock epoch so the web syncs its playhead."""
        base = self.endpoint_url.split("/api/v1", 1)[0]
        url = f"{base}/api/v1/stream/clock"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}",
        }
        body = {"cameraId": camera_id, "epoch": epoch, "duration": self._duration or 0.0}
        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(url, json=body, headers=headers)
                if response.status_code == 200:
                    print(f"[EvidenceClip] Stream clock registered camera={camera_id} epoch={epoch:.3f}")
                    return True
                print(f"[EvidenceClip] Stream clock attempt {attempt}/{self.max_retries} HTTP {response.status_code}")
            except httpx.TransportError as exc:
                print(f"[EvidenceClip] Stream clock attempt {attempt}/{self.max_retries} error: {type(exc).__name__}")
            if attempt < self.max_retries:
                time.sleep(0.2 * (2 ** (attempt - 1)))
        return False

    def _mark_artifact_ready(self, incident_id: int, clip_url: str) -> bool:
        """Backfill the rendered clip URL onto the incident shown in the UI."""
        if not self.bearer_token.strip():
            return False
        update_url = self.endpoint_url.replace("/ingest", f"/{incident_id}/artifact-ready")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}",
        }
        body = {"uri": clip_url, "redactionStatus": "COMPLETE"}
        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(update_url, json=body, headers=headers)
                if response.status_code == 200:
                    print(f"[EvidenceClip] Artifact ready incidentId={incident_id} -> {clip_url}")
                    return True
                print(f"[EvidenceClip] Artifact-ready attempt {attempt}/{self.max_retries} HTTP {response.status_code}")
            except httpx.TransportError as exc:
                print(f"[EvidenceClip] Artifact-ready attempt {attempt}/{self.max_retries} error: {type(exc).__name__}")
            if attempt < self.max_retries:
                time.sleep(0.2 * (2 ** (attempt - 1)))
        return False
