import threading
import time
import warnings
from collections.abc import Callable, Sequence
from typing import Any

from app.config import settings
from app.cv.contracts.cv_event import CVEvent
from app.cv.contracts.validation import validate_event
from app.cv.detector import DEIMv2Detector
from app.cv.event_manager import CVEventManager
from app.cv.events.crowd_adapter import CrowdLifecycleAdapter
from app.cv.events.intrusion_adapter import IntrusionLifecycleAdapter
from app.cv.events.phase7c_abandoned_adapter import Phase7CAbandonedAdapter
from app.cv.frame_sampler import FrameSampler
from app.cv.runtime.adaptive_controller import AdaptiveDecision, AdaptiveInferenceController, AdaptiveSignal
from app.cv.runtime.config import RuntimePerformanceConfig
from app.cv.runtime.metrics import MetricsCollector, PerCameraMetrics
from app.cv.runtime.profiles import parse_per_camera_overrides, resolve_profile
from app.cv.runtime.scheduler import RealtimeScheduler
from app.cv.runtime.tiling import TILE_MODE, infer_tiles
from app.cv.track_store import TrackStore
from app.cv.tracker import ByteTrackMultiObjectTracker
from app.publisher.base import CVEventPublisher
from app.publisher.jsonl_publisher import JsonlPublisher
from app.sources.base import BaseVideoSource
from app.sources.camera_health import CameraHealthMonitor
from app.sources.factory import create_video_source

LIVE_SOURCE_TYPES = {"RTSP", "CAMERA", "LIVE"}


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
        source: BaseVideoSource | None = None,
        scheduler: RealtimeScheduler | None = None,
        performance_config: RuntimePerformanceConfig | None = None,
        metrics: MetricsCollector | None = None,
    ):
        self.camera_id = camera_id
        self.processed_frames = 0
        self.event_id_namespace = candidate_id_namespace or (lambda value: value)
        if region_validator is not None:
            warnings.warn("region_validator is ignored by the unified CV event worker", DeprecationWarning)

        cam_info = camera_config or next((c for c in settings.cameras if c["camera_id"] == camera_id), None)
        if not cam_info:
            cam_info = {
                "camera_id": camera_id,
                "source_type": "SIMULATED",
                "source_uri": source_uri or "./tests/clips/intrusion_positive.mp4",
                "inference_fps": 5.0,
            }
        uri = source_uri or cam_info.get("source_uri", "./tests/clips/intrusion_positive.mp4")
        fps = float(cam_info.get("inference_fps", 5.0))

        self.source = source or create_video_source({**cam_info, "source_uri": uri, "inference_fps": fps})
        continuity = cam_info.get("continuity", {})
        self.reset_after_s = float(continuity.get("reset_after_s", 5.0))
        self.outage_reset_count = 0
        self.health_monitor = CameraHealthMonitor(camera_id=camera_id)
        self.health_monitor.attach_source(self.source)
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
        self.adapters = (
            tuple(adapters)
            if adapters is not None
            else (
                IntrusionLifecycleAdapter(camera_id, zones, rules),
                CrowdLifecycleAdapter(camera_id, zones, rules),
                Phase7CAbandonedAdapter(camera_id, phase7c_config, fps),
            )
        )
        self.event_manager = event_manager or CVEventManager(camera_id)
        self.publisher = publisher or JsonlPublisher(output_path=settings.artifact_dir / "events" / "cv-events.jsonl")
        override = parse_per_camera_overrides(cam_info)
        self.performance_config = performance_config or RuntimePerformanceConfig.from_mapping(
            settings.runtime_performance, override
        )
        self.profile = resolve_profile(override.get("profile") or self.performance_config.profile, self.performance_config)
        self.scheduler = scheduler
        self.metrics_collector = metrics
        self.adaptive_controller: AdaptiveInferenceController | None = None
        self._runtime_signal: AdaptiveSignal | None = None

    def run(
        self,
        max_frames: int | None = None,
        stop_event: threading.Event | None = None,
        deadline: float | None = None,
    ) -> list[CVEvent]:
        generated_events: list[CVEvent] = []
        processed_count = 0
        configure_stop = getattr(self.source, "configure_stop", None)
        if callable(configure_stop):
            configure_stop(stop_event, deadline)
        configure_outage = getattr(self.source, "configure_outage_handler", None)
        if callable(configure_outage):
            configure_outage(
                self.reset_after_s,
                lambda outage_s: self._handle_long_outage(outage_s, generated_events),
            )
        self._ensure_runtime()
        try:
            if self.detector is None:
                self.detector = self.detector_factory()
            scheduler = getattr(self, "scheduler", None)
            for frame_data in self.source.read_frames():
                if self._should_stop(stop_event, deadline):
                    break
                self._reset_after_long_outage(generated_events)
                self.health_monitor.update_frame_time(frame_data.captured_at)

                decision = self._decide(frame_data)
                if decision is not None:
                    self.frame_sampler.inference_fps = decision.target_inference_fps
                if self._should_drop_stale(frame_data, decision):
                    self._record_skip(frame_data, dropped=True)
                    continue
                if not self.frame_sampler.should_process(frame_data):
                    self._record_skip(frame_data, dropped=False)
                    continue

                if scheduler is not None:
                    if not scheduler.await_turn(self.camera_id, lambda: self._should_stop(stop_event, deadline)):
                        break
                try:
                    detections, latency_ms = self._run_inference(frame_data, decision)
                    track_results = self.tracker.track(detections, frame_data)
                    active_snapshot = tuple(self.track_store.update_track(track) for track in track_results)
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
                finally:
                    if scheduler is not None:
                        scheduler.release_turn()

                processed_count += 1
                self.processed_frames = processed_count
                record_processed = getattr(self.health_monitor, "record_processed", None)
                if callable(record_processed):
                    record_processed(latency_ms)
                self._record_inferred(frame_data, decision, latency_ms)
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

    def _ensure_runtime(self) -> None:
        """Lazily construct the adaptive controller when not injected.

        Workers assembled directly (e.g. unit tests via ``__new__``) may not
        carry the performance config; for those the controller stays absent and
        the worker behaves exactly like the pre-Phase-10B path.
        """
        controller = getattr(self, "adaptive_controller", None)
        if controller is not None:
            return
        perf_config = getattr(self, "performance_config", None)
        profile = getattr(self, "profile", None)
        if perf_config is None or profile is None:
            return
        self.adaptive_controller = AdaptiveInferenceController(perf_config, self.camera_id, profile=profile)

    def _build_signal(self, frame_data) -> AdaptiveSignal:
        area = 0.0
        image = getattr(frame_data, "image", None)
        if image is not None:
            area = float(getattr(image, "shape", [0, 0])[0] * getattr(image, "shape", [0, 0])[1])
        scheduler_wait = 0.0
        if self.scheduler is not None and self.metrics_collector is not None:
            scheduler_wait = self.metrics_collector.camera(self.camera_id).scheduler_wait_ms
        recent = self.health_monitor.last_inference_latency_ms or 0.0
        pipeline = float(recent) + float(scheduler_wait)
        return AdaptiveSignal(
            camera_id=self.camera_id,
            source_resolution_area=area,
            recent_detector_latency_ms=float(recent),
            recent_pipeline_latency_ms=pipeline,
            actual_fps=self.health_monitor.frames_processed,
            dropped_ratio=self._dropped_ratio(),
            has_active_event=self._has_active_event(),
        )

    def _decide(self, frame_data) -> AdaptiveDecision | None:
        controller = getattr(self, "adaptive_controller", None)
        if controller is None:
            return None
        self._runtime_signal = self._build_signal(frame_data)
        return controller.decide(self._runtime_signal)

    def _should_drop_stale(self, frame_data, decision: AdaptiveDecision | None) -> bool:
        perf_config = getattr(self, "performance_config", None)
        if perf_config is None:
            return False
        if str(frame_data.source_type).upper() not in LIVE_SOURCE_TYPES:
            return False
        budget = perf_config.latency_budget
        age_ms = self._frame_age_ms(frame_data)
        if age_ms is None:
            return False
        state = decision.overload_state.value if decision is not None else "NORMAL"
        if age_ms > budget.overloaded_ms:
            return True
        if state in ("DEGRADED", "OVERLOADED") and age_ms > budget.acceptable_ms:
            return True
        return False

    def _frame_age_ms(self, frame_data) -> float | None:
        try:
            from app.common.time_utils import parse_iso_timestamp

            captured = parse_iso_timestamp(frame_data.captured_at)
            now = time.time()
            age = (now - captured.timestamp()) * 1000.0
        except (ValueError, TypeError, OverflowError):
            return None
        return max(0.0, age)

    def _run_inference(self, frame_data, decision: AdaptiveDecision | None):
        mode = decision.inference_mode if decision is not None else "full640"
        config = getattr(self, "performance_config", None)
        if config is not None and mode == TILE_MODE and config.adaptive.enabled and getattr(frame_data, "image", None) is not None:
            nms = float(settings.detector_config.get("nms_iou_threshold", 0.5))
            return infer_tiles(
                self.detector,
                frame_data,
                tile_size=config.adaptive.tile_size,
                overlap_ratio=config.adaptive.overlap_ratio,
                nms_iou_threshold=nms,
            )
        return self.detector.detect(frame_data)

    def _dropped_ratio(self) -> float:
        metrics = getattr(self, "metrics_collector", None)
        if metrics is None:
            return 0.0
        snap = metrics.camera(self.camera_id).snapshot()
        return float(snap.get("dropped_ratio", 0.0))

    def _has_active_event(self) -> bool:
        manager = getattr(self, "event_manager", None)
        probe = getattr(manager, "has_active_events", None)
        if callable(probe):
            try:
                if probe():
                    return True
            except Exception:
                pass
        for adapter in self.adapters:
            adapter_probe = getattr(adapter, "has_active_event", None)
            if callable(adapter_probe):
                try:
                    if adapter_probe():
                        return True
                except Exception:
                    continue
        return False

    def _record_skip(self, frame_data, dropped: bool) -> None:
        record_skipped = getattr(self.health_monitor, "record_skipped", None)
        if callable(record_skipped):
            record_skipped()
        collector = getattr(self, "metrics_collector", None)
        if collector is None:
            return
        metrics = collector.camera(self.camera_id)
        metrics.source_fps = getattr(frame_data, "source_fps", 0.0) or 0.0
        metrics.frames_received += 1
        if dropped:
            metrics.frames_dropped += 1
            collector.record_drop(self.camera_id)
        else:
            metrics.frames_skipped += 1

    def _record_inferred(self, frame_data, decision: AdaptiveDecision | None, latency_ms: float) -> None:
        collector = getattr(self, "metrics_collector", None)
        if collector is None:
            return
        metrics = collector.camera(self.camera_id)
        metrics.source_fps = getattr(frame_data, "source_fps", 0.0) or 0.0
        metrics.frames_received += 1
        metrics.detector_latency_ms = float(latency_ms)
        age = self._frame_age_ms(frame_data)
        metrics.frame_age_at_inference_ms = age if age is not None else 0.0
        metrics.target_inference_fps = self.frame_sampler.inference_fps
        metrics.profile = getattr(self.profile, "name", "BALANCED")
        if decision is not None:
            metrics.inference_mode = decision.inference_mode
            metrics.overload_state = decision.overload_state.value
        metrics.mark_infer()
        collector.record_detector(self.camera_id, float(latency_ms))

    def _reset_after_long_outage(self, generated_events: list[CVEvent]) -> None:
        consume = getattr(self.source, "consume_outage_duration", None)
        outage_s = consume() if callable(consume) else None
        if outage_s is None:
            return
        self._handle_long_outage(outage_s, generated_events)

    def _handle_long_outage(self, outage_s: float, generated_events: list[CVEvent]) -> None:
        if outage_s < self.reset_after_s:
            return
        self._end_active_lifecycles(generated_events)
        for component in (*self.adapters, self.tracker, self.track_store):
            reset = getattr(component, "reset", None)
            if callable(reset):
                reset()
        self.event_manager = CVEventManager(self.camera_id)
        self.outage_reset_count += 1

    def _end_active_lifecycles(self, generated_events: list[CVEvent]) -> None:
        end_all = getattr(self.event_manager, "end_all", None)
        if not callable(end_all):
            return
        for event in end_all():
            original_event_id = event.event_id
            event = self._namespace_event(event)
            self._publish(event, original_event_id)
            generated_events.append(event)

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
        self._end_active_lifecycles(generated_events)
        for component in (*self.adapters, self.event_manager):
            finalize = getattr(component, "finalize", None)
            if callable(finalize):
                finalize()

    @staticmethod
    def _should_stop(stop_event: threading.Event | None, deadline: float | None) -> bool:
        return bool(
            (stop_event is not None and stop_event.is_set()) or (deadline is not None and time.monotonic() >= deadline)
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
            "person_high_conf",
            "person_median_conf",
            "person_rolling_high_ratio",
            "person_min_rolling_good_ratio",
            "person_min_global_high_ratio",
            "luggage_high_conf",
            "luggage_median_conf",
            "luggage_rolling_high_ratio",
            "luggage_min_rolling_good_ratio",
            "luggage_min_global_high_ratio",
            "max_spread_norm",
            "max_net_displacement_norm",
            "min_association_score",
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
