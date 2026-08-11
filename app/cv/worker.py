from collections.abc import Callable
from typing import Any

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


class CVWorker:
    def __init__(self, camera_id: str, source_uri: str | None = None, publisher: EventPublisher | None = None,
                 detector: DEIMv2Detector | None = None, tracker: Any | None = None,
                 detector_factory: Callable[[], DEIMv2Detector] | None = None):
        self.camera_id = camera_id

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
        validator = create_region_validator(vlm_cfg.get("mode", "disabled"),
                                            model=vlm_cfg.get("model", "google/gemma-3-4b-it"),
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
            publisher = HttpEventPublisher(endpoint_url=settings.event_ingest_url)
        self.publisher = publisher

    def run(self, max_frames: int | None = None) -> list[EventCandidate]:
        generated_candidates: list[EventCandidate] = []
        processed_count = 0

        try:
            # Resolve before reading frames, but inside the cleanup boundary so a
            # startup failure still releases source and pending engine resources.
            if self.detector is None:
                self.detector = self.detector_factory()
            for frame_data in self.source.read_frames():
                self.health_monitor.update_frame_time(frame_data.captured_at)

                if not self.frame_sampler.should_process(frame_data):
                    continue

            # 1. Detection
                detections, latency_ms = self.detector.detect(frame_data)

            # 2. Tracking
                track_results = self.tracker.track(detections, frame_data)

            # 3. Track Store Update
                active_tracks = []
                for tr in track_results:
                    track_state = self.track_store.update_track(tr)
                    active_tracks.append(track_state)

            # 4. Evaluate across registered Event Engines
                regions = self.static_region_detector.update(frame_data.image, frame_data.captured_at)
                self.abandoned_engine.submit_static_regions(regions)
                for engine in self.engines:
                    candidates = engine.evaluate(active_tracks, frame_data)
                    for candidate in candidates:
                        self.publisher.publish(candidate)
                        generated_candidates.append(candidate)

                processed_count += 1
                if max_frames and processed_count >= max_frames:
                    break
        finally:
            self.abandoned_engine.finalize()
            self.source.release()
        return generated_candidates
