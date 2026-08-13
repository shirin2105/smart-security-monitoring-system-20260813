from collections.abc import Callable
from typing import Any
import threading
import time

from app.common.schemas import EventCandidate
from app.config import settings
from app.cv.detector import DEIMv2Detector
from app.cv.frame_sampler import FrameSampler
from app.cv.static_region_detector import StaticRegionDetector
from app.cv.track_store import TrackStore
from app.cv.tracker import ByteTrackMultiObjectTracker
from app.events.abandoned_object import AbandonedObjectEngine
from app.events.crowd import CrowdEventEngine
from app.events.intrusion import IntrusionEventEngine
from app.publisher.base import EventPublisher
from app.publisher.http_publisher import HttpEventPublisher
from app.sources.camera_health import CameraHealthMonitor
from app.sources.mp4_source import MP4VideoSource
from app.vlm.region_validator import create_region_validator
from app.vlm.region_validator import RegionValidator


class CVWorker:
    def __init__(self, camera_id: str, source_uri: str | None = None, publisher: EventPublisher | None = None,
                 detector: DEIMv2Detector | None = None, tracker: Any | None = None,
                 detector_factory: Callable[[], DEIMv2Detector] | None = None,
                 region_validator: RegionValidator | None = None,
                 candidate_id_namespace: Callable[[str], str] | None = None,
                 loop: bool = True,
                 realtime: bool = False,
                 **kwargs: Any):
        self.camera_id = camera_id
        self.candidate_id_namespace = candidate_id_namespace or (lambda value: value)
        self.realtime = realtime

        # Load configs
        cameras_cfg = settings.cameras
        cam_info = next((c for c in cameras_cfg if c["camera_id"] == camera_id), None)
        if not cam_info:
            cam_info = {
                "camera_id": camera_id,
                "source_type": "SIMULATED",
                "source_uri": source_uri or "./tests/clips/intrusion_positive.mp4",
                "inference_fps": 5.0,
            }

        uri = source_uri or cam_info.get("source_uri", "./tests/clips/intrusion_positive.mp4")

        self.source = MP4VideoSource(
            camera_id=camera_id,
            source_uri=uri,
            source_type=cam_info.get("source_type", "SIMULATED"),
            inference_fps=cam_info.get("inference_fps", 5.0),
            loop=loop,
        )
        self.health_monitor = CameraHealthMonitor(camera_id=camera_id)
        self.frame_sampler = FrameSampler(inference_fps=cam_info.get("inference_fps", 5.0))

        models_cfg = settings.detector_config
        self.detector = detector
        self.detector_factory = detector_factory or (lambda: DEIMv2Detector(**models_cfg))
        self.tracker = tracker or ByteTrackMultiObjectTracker(
            camera_id=camera_id, frame_rate=cam_info.get("inference_fps", 5.0)
        )
        self.track_store = TrackStore(camera_id=camera_id)
        abandoned_rules = settings.event_rules.get("abandoned_object", {})
        self.static_region_detector = StaticRegionDetector(camera_id, abandoned_rules.get("static_region", {}))

        # All CV Event Engines Registered
        vlm_cfg = abandoned_rules.get("vlm", {})
        validator = region_validator or create_region_validator(
            vlm_cfg.get("mode", "disabled"), model=vlm_cfg.get("model", "google/gemma-3-4b-it"),
            timeout_seconds=vlm_cfg.get("timeout_seconds", 8.0))
        self.engines = [
            IntrusionEventEngine(
                camera_id=camera_id,
                zones_config=settings.zones,
                rules_config=settings.event_rules,
            ),
            CrowdEventEngine(
                camera_id=camera_id,
                zones_config=settings.zones,
                rules_config=settings.event_rules,
            ),
            AbandonedObjectEngine(
                camera_id=camera_id,
                zones_config=settings.zones,
                rules_config=settings.event_rules,
                region_validator=validator,
            ),
        ]
        self.abandoned_engine = self.engines[-1]
        if publisher is None:
            publisher = HttpEventPublisher(
                endpoint_url=settings.event_ingest_url,
                bearer_token=settings.event_ingest_token,
                timeout_seconds=settings.event_ingest_timeout_seconds,
                max_retries=settings.event_ingest_max_attempts,
            )
        self.publisher = publisher

    def run(self, max_frames: int | None = None, stop_event: threading.Event | None = None,
            deadline: float | None = None) -> list[EventCandidate]:
        generated_candidates: list[EventCandidate] = []
        processed_count = 0
        start_wall_time: float | None = None
        prev_frame_id: int | None = None

        try:
            # Resolve before reading frames, but inside the cleanup boundary so a
            # startup failure still releases source and pending engine resources.
            if self.detector is None:
                self.detector = self.detector_factory()
            for frame_data in self.source.read_frames():
                if (stop_event is not None and stop_event.is_set()) or (deadline is not None and time.monotonic() >= deadline):
                    break
                self.health_monitor.update_frame_time(frame_data.captured_at)

                if not self.frame_sampler.should_process(frame_data):
                    continue

                src_fps = frame_data.source_fps if frame_data.source_fps > 0 else 25.0
                video_time = float((frame_data.frame_id - 1) / src_fps)

                if getattr(self, "realtime", False):
                    now = time.monotonic()
                    if start_wall_time is None or (prev_frame_id is not None and frame_data.frame_id < prev_frame_id):
                        start_wall_time = now - video_time
                    expected_wall_time = start_wall_time + video_time
                    sleep_dur = expected_wall_time - now
                    if sleep_dur > 0:
                        if stop_event is not None:
                            if stop_event.wait(timeout=sleep_dur):
                                break
                        else:
                            time.sleep(sleep_dur)
                    prev_frame_id = frame_data.frame_id

            # 1. Detection
                detections, latency_ms = self.detector.detect(frame_data)

            # 2. Tracking
                track_results = self.tracker.track(detections, frame_data)

            # 3. Track Store Update
                active_tracks = []
                for tr in track_results:
                    track_state = self.track_store.update_track(tr)
                    active_tracks.append(track_state)

                # Publish real-time frame telemetry for Dev Mode
                if hasattr(self.publisher, "publish_telemetry"):
                    frame_h, frame_w = (frame_data.image.shape[:2] if frame_data.image is not None else (480, 640))
                    person_tracks = [tr for tr in active_tracks if tr.class_name == "person"]
                    telemetry_tracks = [
                        {
                            "trackId": tr.track_id,
                            "className": tr.class_name,
                            "confidence": round(float(tr.confidence), 3),
                            "bbox": [round(float(c), 2) for c in tr.latest_bbox],
                        }
                        for tr in person_tracks
                    ]
                    ts_str = frame_data.captured_at if isinstance(frame_data.captured_at, str) else frame_data.captured_at.isoformat()
                    video_time = round(float((frame_data.frame_id - 1) / (frame_data.source_fps if frame_data.source_fps > 0 else 25.0)), 3)
                    telemetry_payload = {
                        "cameraId": self.camera_id,
                        "timestamp": ts_str,
                        "videoTime": video_time,
                        "frameSize": [frame_w, frame_h],
                        "tracks": telemetry_tracks,
                    }
                    self.publisher.publish_telemetry(telemetry_payload)


            # 4. Evaluate across registered Event Engines
                regions = self.static_region_detector.update(frame_data.image, frame_data.captured_at)
                self.abandoned_engine.submit_static_regions(regions)
                for engine in self.engines:
                    candidates = engine.evaluate(active_tracks, frame_data)
                    for candidate in candidates:
                        if (stop_event is not None and stop_event.is_set()) or (deadline is not None and time.monotonic() >= deadline):
                            break
                        namespace_fn = getattr(self, "candidate_id_namespace", lambda value: value)
                        namespaced_id = namespace_fn(candidate.candidateId)
                        if namespaced_id != candidate.candidateId:
                            candidate = candidate.model_copy(update={"candidateId": namespaced_id})
                        self.publisher.publish(candidate)
                        generated_candidates.append(candidate)

                processed_count += 1
                if max_frames and processed_count >= max_frames:
                    break
        finally:
            self.abandoned_engine.finalize()
            self.source.release()
        return generated_candidates
