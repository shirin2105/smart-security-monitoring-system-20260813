from collections.abc import Callable, Sequence
from typing import Any
import threading
import time
import warnings

from app.config import settings
from app.cv.contracts.cv_event import CVEvent
from app.cv.contracts.validation import validate_event
from app.cv.detector import DEIMv2Detector
from app.cv.event_manager import CVEventManager
from app.cv.events.crowd_adapter import CrowdLifecycleAdapter
from app.cv.events.intrusion_adapter import IntrusionLifecycleAdapter
from app.cv.events.phase7c_abandoned_adapter import Phase7CAbandonedAdapter
from app.cv.frame_sampler import FrameSampler
from app.cv.track_store import TrackStore
from app.cv.tracker import ByteTrackMultiObjectTracker
from app.publisher.base import CVEventPublisher
from app.publisher.jsonl_publisher import JsonlPublisher
from app.sources.camera_health import CameraHealthMonitor
from app.sources.mp4_source import MP4VideoSource


class CVWorker:
    def __init__(
        self,
        camera_id: str,
        source_uri: str | None = None,
        publisher: CVEventPublisher | None = None,
        detector: DEIMv2Detector | None = None,
        tracker: Any | None = None,
        detector_factory: Callable[[], DEIMv2Detector] | None = None,
        region_validator: Any | None = None,
        candidate_id_namespace: Callable[[str], str] | None = None,
        adapters: Sequence[Any] | None = None,
        event_manager: CVEventManager | None = None,
        camera_config: dict[str, Any] | None = None,
        zones_config: list[dict[str, Any]] | None = None,
        rules_config: dict[str, Any] | None = None,
        loop: bool = True,
        realtime: bool = False,
    ):
        self.camera_id = camera_id
        self.processed_frames = 0
        self.realtime = realtime
        self.event_id_namespace = candidate_id_namespace or (lambda value: value)
        if region_validator is not None:
            warnings.warn("region_validator is ignored by the unified CV event worker", DeprecationWarning)

        cam_info = camera_config or next(
            (c for c in settings.cameras if c["camera_id"] == camera_id), None
        )
        if not cam_info:
            cam_info = {
                "camera_id": camera_id,
                "source_type": "SIMULATED",
                "source_uri": source_uri or "./tests/clips/intrusion_positive.mp4",
                "inference_fps": 5.0,
            }
        uri = source_uri or cam_info.get("source_uri", "./tests/clips/intrusion_positive.mp4")
        fps = float(cam_info.get("inference_fps", 5.0))

        self.source = MP4VideoSource(
            camera_id, uri, cam_info.get("source_type", "SIMULATED"), fps, loop=loop
        )
        self.health_monitor = CameraHealthMonitor(camera_id=camera_id)
        self.frame_sampler = FrameSampler(inference_fps=fps)
        self.detector = detector
        self.detector_factory = detector_factory or (lambda: DEIMv2Detector(**settings.detector_config))
        self.tracker = tracker or ByteTrackMultiObjectTracker(camera_id=camera_id, frame_rate=fps)
        self.track_store = TrackStore(camera_id=camera_id)

        rules = rules_config or settings.event_rules
        zones = zones_config if zones_config is not None else settings.zones
        abandoned = rules.get("abandoned_object", {})
        if any(key in abandoned for key in ("static_region", "vlm", "candidate_source")):
            warnings.warn(
                "legacy abandoned_object static-region/VLM settings are ignored by the unified worker",
                DeprecationWarning,
            )
        phase7c_config = abandoned.get("phase7c", {})
        self._validate_phase7c_config(phase7c_config)
        self.adapters = tuple(adapters) if adapters is not None else (
            IntrusionLifecycleAdapter(camera_id, zones, rules),
            CrowdLifecycleAdapter(camera_id, zones, rules),
            Phase7CAbandonedAdapter(camera_id, phase7c_config, fps),
        )
        self.event_manager = event_manager or CVEventManager(camera_id)
        self.publisher = publisher or JsonlPublisher(
            output_path=settings.artifact_dir / "events" / "cv-events.jsonl"
        )

    def run(
        self,
        max_frames: int | None = None,
        stop_event: threading.Event | None = None,
        deadline: float | None = None,
    ) -> list[CVEvent]:
        generated_events: list[CVEvent] = []
        processed_count = 0
        start_wall_time: float | None = None
        previous_frame_id: int | None = None
        try:
            if self.detector is None:
                self.detector = self.detector_factory()
            for frame_data in self.source.read_frames():
                if self._should_stop(stop_event, deadline):
                    break
                self.health_monitor.update_frame_time(frame_data.captured_at)
                if not self.frame_sampler.should_process(frame_data):
                    continue

                if self.realtime:
                    source_fps = frame_data.source_fps if frame_data.source_fps > 0 else 25.0
                    media_time = (frame_data.frame_id - 1) / source_fps
                    now = time.monotonic()
                    if start_wall_time is None or (
                        previous_frame_id is not None and frame_data.frame_id < previous_frame_id
                    ):
                        start_wall_time = now - media_time
                    remaining = start_wall_time + media_time - now
                    if remaining > 0 and stop_event is not None and stop_event.wait(remaining):
                        break
                    if remaining > 0 and stop_event is None:
                        time.sleep(remaining)
                    previous_frame_id = frame_data.frame_id

                detections, _latency_ms = self.detector.detect(frame_data)
                track_results = self.tracker.track(detections, frame_data)
                active_snapshot = tuple(
                    self.track_store.update_track(track) for track in track_results
                )
                for adapter in self.adapters:
                    for signal in adapter.evaluate(active_snapshot, frame_data):
                        if self._should_stop(stop_event, deadline):
                            break
                        event = self.event_manager.process(signal)
                        if event is None:
                            continue
                        original_event_id = event.event_id
                        event = self._namespace_event(event)
                        self._publish(event, original_event_id)
                        generated_events.append(event)

                processed_count += 1
                self.processed_frames = processed_count
                if max_frames is not None and processed_count >= max_frames:
                    break
        except BaseException as primary_error:
            try:
                self._cleanup(generated_events)
            except BaseException as cleanup_error:
                primary_error.add_note(f"CV cleanup also failed: {cleanup_error!r}")
            try:
                self.source.release()
            except BaseException as release_error:
                primary_error.add_note(f"CV source release also failed: {release_error!r}")
            raise
        else:
            try:
                self._cleanup(generated_events)
            finally:
                self.source.release()
        return generated_events

    def _publish(self, event: CVEvent, lifecycle_event_id: str | None = None) -> None:
        validate_event(event)
        rollback_id = lifecycle_event_id or event.event_id
        try:
            published = self.publisher.publish(event)
        except BaseException:
            if event.event_state == "START":
                self.event_manager.discard(rollback_id)
            raise
        if published is False:
            if event.event_state == "START":
                self.event_manager.discard(rollback_id)
            raise RuntimeError(f"failed to publish CVEvent {event.event_id}")

    def _cleanup(self, generated_events: list[CVEvent]) -> None:
        end_all = getattr(self.event_manager, "end_all", None)
        ending_events = end_all() if callable(end_all) else []
        for event in ending_events:
            original_event_id = event.event_id
            event = self._namespace_event(event)
            self._publish(event, original_event_id)
            generated_events.append(event)
        for component in (*self.adapters, self.event_manager):
            finalize = getattr(component, "finalize", None)
            if callable(finalize):
                finalize()

    @staticmethod
    def _should_stop(stop_event: threading.Event | None, deadline: float | None) -> bool:
        return bool(
            (stop_event is not None and stop_event.is_set())
            or (deadline is not None and time.monotonic() >= deadline)
        )

    def _namespace_event(self, event: CVEvent) -> CVEvent:
        event_id = self.event_id_namespace(event.event_id)
        if event_id == event.event_id:
            return event
        return CVEvent.from_dict({**event.to_dict(), "event_id": event_id})

    @staticmethod
    def _validate_phase7c_config(config: dict[str, Any]) -> None:
        if not isinstance(config, dict):
            raise ValueError("abandoned_object.phase7c must be an object")
        ratio_fields = {
            "person_high_conf", "person_median_conf", "person_rolling_high_ratio",
            "person_min_rolling_good_ratio", "person_min_global_high_ratio",
            "luggage_high_conf", "luggage_median_conf", "luggage_rolling_high_ratio",
            "luggage_min_rolling_good_ratio", "luggage_min_global_high_ratio",
            "max_spread_norm", "max_net_displacement_norm", "min_association_score",
        }
        for section in ("quality", "stitch", "stationary", "owner"):
            values = config.get(section, {})
            if not isinstance(values, dict):
                raise ValueError(f"abandoned_object.phase7c.{section} must be an object")
            for key, value in values.items():
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError(f"abandoned_object.phase7c.{section}.{key} must be numeric")
                if value < 0 or (key == "min_samples" and value < 1):
                    raise ValueError(f"abandoned_object.phase7c.{section}.{key} is out of range")
                if key in ratio_fields and value > 1:
                    raise ValueError(f"abandoned_object.phase7c.{section}.{key} must be <= 1")
        roi = config.get("valid_floor_roi_polygon")
        if roi is not None and (
            not isinstance(roi, list)
            or len(roi) < 3
            or any(not isinstance(point, (list, tuple)) or len(point) != 2 for point in roi)
        ):
            raise ValueError("abandoned_object.phase7c.valid_floor_roi_polygon must be a polygon")
