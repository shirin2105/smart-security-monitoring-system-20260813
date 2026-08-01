import math
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from app.common.enums import EventType, SourceEngine
from app.common.schemas import (EventCandidate, ObservationData, FrameData, StaticRegionObservation,
                                VLMValidationResult)
from app.common.time_utils import calculate_duration_seconds, utc_now_iso
from app.events.base import BaseEventEngine
from app.events.dedupe import EventDedupeManager
from app.cv.track_store import TrackState
from app.cv.evidence import EvidenceCapture
from app.vlm.region_validator import (DisabledRegionValidator, RegionValidator, TemporalFrame,
                                      validate_temporal_compat)


class AbandonedObjectState(str, Enum):
    MOVING = "MOVING"
    STATIONARY_PENDING = "STATIONARY_PENDING"
    STATIONARY = "STATIONARY"
    OWNER_LEFT_PENDING = "OWNER_LEFT_PENDING"
    ABANDONED_CANDIDATE = "ABANDONED_CANDIDATE"
    CLEARED = "CLEARED"


def calculate_bbox_center(bbox: List[float]) -> Tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def calculate_euclidean_distance(pt1: Tuple[float, float], pt2: Tuple[float, float]) -> float:
    return math.hypot(pt1[0] - pt2[0], pt1[1] - pt2[1])


class ObjectStateTracker:
    def __init__(
        self,
        track_id: int,
        first_frame_id: int,
        class_name: str = "bag",
        stationary_seconds: float = 15.0,
        stationary_pixel_threshold: float = 12.0,
        owner_association_distance: float = 150.0,
        owner_absent_seconds: float = 10.0,
    ):
        self.track_id = track_id
        self.first_frame_id = first_frame_id
        self.class_name = class_name
        self.stationary_seconds = stationary_seconds
        self.stationary_pixel_threshold = stationary_pixel_threshold
        self.owner_association_distance = owner_association_distance
        self.owner_absent_seconds = owner_absent_seconds

        self.current_state: AbandonedObjectState = AbandonedObjectState.MOVING
        self.stationary_started_at: Optional[str] = None
        self.owner_left_started_at: Optional[str] = None

        self.owner_track_id: Optional[int] = None
        self.center_history: List[Tuple[float, float]] = []
        self.last_known_bbox: Optional[List[float]] = None
        self.event_generated: bool = False
        self.frames_since_last_detection: int = 0

    def update(
        self,
        bbox: Optional[List[float]],
        timestamp: str,
        active_person_tracks: List[TrackState],
        frame_id: int,
    ) -> AbandonedObjectState:
        # Ignore objects present from frame 1 to avoid baseline static scene false positives
        if self.first_frame_id <= 1:
            return self.current_state

        if bbox is not None:
            self.last_known_bbox = bbox
            self.frames_since_last_detection = 0
            center = calculate_bbox_center(bbox)
            self.center_history.append(center)
        else:
            self.frames_since_last_detection += 1
            if self.last_known_bbox is None:
                return self.current_state
            center = calculate_bbox_center(self.last_known_bbox)

        # Associate owner candidate on initial appearance
        if self.owner_track_id is None and active_person_tracks:
            closest_dist = float("inf")
            closest_p_id = None
            for p in active_person_tracks:
                p_foot = p.latest_foot_point
                dist = calculate_euclidean_distance(center, p_foot)
                if dist < self.owner_association_distance and dist < closest_dist:
                    closest_dist = dist
                    closest_p_id = p.track_id
            self.owner_track_id = closest_p_id

        # Calculate average displacement over center history
        if len(self.center_history) > 1:
            recent_centers = self.center_history[-10:]
            avg_x = sum(c[0] for c in recent_centers) / len(recent_centers)
            avg_y = sum(c[1] for c in recent_centers) / len(recent_centers)
            disp = calculate_euclidean_distance(center, (avg_x, avg_y))
            is_stationary = disp < self.stationary_pixel_threshold
        else:
            is_stationary = True  # Default stationary if no movement history

        # State machine progression
        if self.current_state == AbandonedObjectState.MOVING:
            if is_stationary:
                self.current_state = AbandonedObjectState.STATIONARY_PENDING
                self.stationary_started_at = timestamp

        elif self.current_state == AbandonedObjectState.STATIONARY_PENDING:
            if is_stationary:
                stat_dur = calculate_duration_seconds(self.stationary_started_at, timestamp)
                if stat_dur >= self.stationary_seconds:
                    self.current_state = AbandonedObjectState.STATIONARY
            else:
                self.current_state = AbandonedObjectState.MOVING
                self.stationary_started_at = None

        elif self.current_state == AbandonedObjectState.STATIONARY:
            # Check owner absence
            owner_present = False
            if self.owner_track_id is not None:
                for p in active_person_tracks:
                    if p.track_id == self.owner_track_id:
                        p_foot = p.latest_foot_point
                        if calculate_euclidean_distance(center, p_foot) < self.owner_association_distance:
                            owner_present = True
                            break

            if not owner_present:
                self.current_state = AbandonedObjectState.OWNER_LEFT_PENDING
                self.owner_left_started_at = timestamp

        elif self.current_state == AbandonedObjectState.OWNER_LEFT_PENDING:
            owner_present = False
            if self.owner_track_id is not None:
                for p in active_person_tracks:
                    if p.track_id == self.owner_track_id:
                        p_foot = p.latest_foot_point
                        if calculate_euclidean_distance(center, p_foot) < self.owner_association_distance:
                            owner_present = True
                            break

            if not owner_present:
                left_dur = calculate_duration_seconds(self.owner_left_started_at, timestamp)
                if left_dur >= self.owner_absent_seconds:
                    self.current_state = AbandonedObjectState.ABANDONED_CANDIDATE
            else:
                self.current_state = AbandonedObjectState.STATIONARY
                self.owner_left_started_at = None

        return self.current_state


class RegionEventState:
    def __init__(self, observation: StaticRegionObservation):
        self.observation = observation
        self.owner_track_id: Optional[int] = None
        self.owner_left_started_at: Optional[str] = None
        self.event_generated = False
        self.pending: Optional[PendingRegionValidation] = None


@dataclass(frozen=True)
class PendingRegionValidation:
    observation: StaticRegionObservation
    event_time: str
    person_count: int
    absent_seconds: float
    source_type: str


def _timestamp(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


class AbandonedObjectEngine(BaseEventEngine):
    ALLOWED_CLASSES = {"backpack", "handbag", "suitcase"}

    def __init__(
        self,
        camera_id: str,
        zones_config: List[Dict[str, Any]],
        rules_config: Dict[str, Any],
        evidence_capture: Optional[EvidenceCapture] = None,
        region_validator: Optional[RegionValidator] = None,
    ):
        self.camera_id = camera_id
        rules = rules_config.get("abandoned_object", {})
        self.stationary_seconds = float(rules.get("stationary_seconds", 15.0))
        self.stationary_pixel_threshold = float(rules.get("stationary_pixel_threshold", 12.0))
        self.owner_association_distance = float(rules.get("owner_association_distance", 150.0))
        self.owner_absent_seconds = float(rules.get("owner_absent_seconds", 10.0))
        self.cooldown_seconds = float(rules.get("cooldown_seconds", 60.0))
        self.candidate_source = rules.get("candidate_source", "tracked_classes")
        temporal = rules.get("temporal", {})
        self.temporal_enabled = bool(temporal.get("enabled", False))
        self.temporal_pre_seconds = max(0.0, float(temporal.get("pre_seconds", 8.0)))
        self.temporal_post_seconds = max(0.0, float(temporal.get("post_seconds", 8.0)))
        self.temporal_sample_fps = max(0.1, float(temporal.get("sample_fps", 1.0)))
        self.temporal_max_frames = max(1, min(17, int(temporal.get("max_frames", 17))))
        self.temporal_max_dimension = max(160, min(1920, int(temporal.get("buffer_max_dimension", 480))))
        self.temporal_buffer_byte_ceiling = max(1_000_000, int(
            temporal.get("buffer_byte_ceiling", 12_000_000)))

        self.object_trackers: Dict[int, ObjectStateTracker] = {}
        self.region_states: Dict[str, RegionEventState] = {}
        self._submitted_regions: List[StaticRegionObservation] = []
        self.dedupe_manager = EventDedupeManager(cooldown_seconds=self.cooldown_seconds)
        self.evidence_capture = evidence_capture or EvidenceCapture()
        self.region_validator = region_validator or DisabledRegionValidator()
        self.region_validation_results: Dict[str, Any] = {}
        self._temporal_frames: List[TemporalFrame] = []
        self.temporal_validation_metadata: Dict[str, Dict[str, Any]] = {}

    def _cache_temporal_result(self, region_id: str, validation: VLMValidationResult,
                               metadata: Dict[str, Any]) -> None:
        self.region_validation_results[region_id] = validation
        self.temporal_validation_metadata[region_id] = metadata
        while len(self.temporal_validation_metadata) > 128:
            oldest = next(iter(self.temporal_validation_metadata))
            self.temporal_validation_metadata.pop(oldest, None)
            if oldest not in self.region_states:
                self.region_validation_results.pop(oldest, None)

    def submit_static_regions(self, regions: List[StaticRegionObservation]) -> None:
        self._submitted_regions = list(regions)

    def _sample_frame(self, frame_data: FrameData) -> None:
        if not self.temporal_enabled or frame_data.image is None:
            return
        now = _timestamp(frame_data.captured_at)
        interval = 1.0 / self.temporal_sample_fps
        if not self._temporal_frames or now - _timestamp(self._temporal_frames[-1].captured_at) >= interval - 1e-6:
            image = frame_data.image
            height, width = image.shape[:2]
            scale = min(1.0, self.temporal_max_dimension / max(height, width))
            if scale < 1.0:
                import cv2
                image = cv2.resize(image, (max(1, round(width * scale)), max(1, round(height * scale))))
            self._temporal_frames.append(TemporalFrame(frame_data.captured_at, image.copy(), width, height))
        pending_starts = [
            _timestamp(state.pending.event_time) - self.temporal_pre_seconds
            for state in self.region_states.values() if state.pending is not None
        ]
        cutoff = min(pending_starts, default=now - self.temporal_pre_seconds)
        self._temporal_frames = [frame for frame in self._temporal_frames if _timestamp(frame.captured_at) >= cutoff]
        hard_cap = max(self.temporal_max_frames + 1,
                       int((self.temporal_pre_seconds + self.temporal_post_seconds) * self.temporal_sample_fps) + 2)
        if len(self._temporal_frames) > hard_cap:
            self._temporal_frames = self._temporal_frames[-hard_cap:]
        while (len(self._temporal_frames) > 1 and
               sum(frame.image.nbytes for frame in self._temporal_frames) > self.temporal_buffer_byte_ceiling):
            self._temporal_frames.pop(0)

    def finalize(self) -> List[str]:
        """Drop incomplete temporal windows at end-of-stream without validating them."""
        pending = [region_id for region_id, state in self.region_states.items()
                   if state.pending is not None and not state.event_generated]
        self._temporal_frames.clear()
        for region_id in pending:
            self.region_states.pop(region_id, None)
            self.region_validation_results.pop(region_id, None)
            self.temporal_validation_metadata.pop(region_id, None)
        self._submitted_regions = []
        return pending

    def _temporal_window(self, event_time: str) -> List[TemporalFrame]:
        center = _timestamp(event_time)
        available = [frame for frame in self._temporal_frames
                     if center - self.temporal_pre_seconds <= _timestamp(frame.captured_at)
                     <= center + self.temporal_post_seconds]
        if len(available) <= self.temporal_max_frames:
            return available
        targets = [center - self.temporal_pre_seconds + index / self.temporal_sample_fps
                   for index in range(self.temporal_max_frames)]
        chosen = {min(available, key=lambda frame: abs(_timestamp(frame.captured_at) - target)).captured_at
                  for target in targets}
        return [frame for frame in available if frame.captured_at in chosen][:self.temporal_max_frames]

    def _build_region_candidate(self, pending: PendingRegionValidation, frame_data: FrameData) -> Optional[EventCandidate]:
        region, timestamp = pending.observation, pending.event_time
        dedupe_key = f"{self.camera_id}:{EventType.ABANDONED_OBJECT.value}:region:{region.region_id}"
        if not self.dedupe_manager.should_emit(dedupe_key, timestamp):
            return None
        safe_id = region.region_id.replace(":", "-")
        candidate_id = f"{self.camera_id}-ABANDONED_OBJECT-{safe_id}-{timestamp.replace(':', '').replace('-', '').replace('.', '')}"
        artifact = self.evidence_capture.capture_evidence(frame_data, candidate_id, None, [region.bbox])
        candidate = EventCandidate(
            candidateId=candidate_id, sourceEngine=SourceEngine.CV, cameraId=self.camera_id,
            sourceType=pending.source_type, eventType=EventType.ABANDONED_OBJECT,
            detectedAt=timestamp, firstSeenAt=region.first_seen_at, lastSeenAt=timestamp,
            confidence=region.confidence, trackCount=0, trackIds=[],
            observations=ObservationData(personCount=pending.person_count,
                stationarySeconds=round(region.persistence_seconds, 2),
                ownerAbsentSeconds=round(pending.absent_seconds, 2)),
            modelVersion="static-region-v1", ruleVersion="abandoned-object-v2", artifact=artifact)
        self.dedupe_manager.record_emitted(dedupe_key, timestamp)
        return candidate

    def _evaluate_regions(self, tracks: List[TrackState], frame_data: FrameData) -> List[EventCandidate]:
        timestamp = frame_data.captured_at
        self._sample_frame(frame_data)
        people = [track for track in tracks if track.class_name == "person"]
        active_ids = {region.region_id for region in self._submitted_regions}
        for region_id in list(self.region_states):
            if region_id not in active_ids and self.region_states[region_id].pending is None:
                del self.region_states[region_id]
                self.region_validation_results.pop(region_id, None)

        candidates = []
        for region in self._submitted_regions:
            state = self.region_states.setdefault(region.region_id, RegionEventState(region))
            state.observation = region
            center = calculate_bbox_center(region.bbox)
            nearby = [p for p in people if calculate_euclidean_distance(center, p.latest_foot_point) < self.owner_association_distance]
            if state.owner_track_id is None and nearby:
                state.owner_track_id = min(nearby, key=lambda p: calculate_euclidean_distance(center, p.latest_foot_point)).track_id
            owner_near = any(p.track_id == state.owner_track_id for p in nearby) if state.owner_track_id is not None else bool(nearby)
            if owner_near:
                state.owner_left_started_at = None
                continue
            if state.owner_left_started_at is None:
                state.owner_left_started_at = timestamp
                continue
            absent = calculate_duration_seconds(state.owner_left_started_at, timestamp)
            if absent < self.owner_absent_seconds or state.event_generated:
                continue
            if self.temporal_enabled:
                if state.pending is None:
                    state.pending = PendingRegionValidation(region, timestamp, len(people), absent,
                                                            frame_data.source_type)
                continue
            if region.region_id not in self.region_validation_results:
                image = frame_data.image
                if image is None:
                    crop = None
                else:
                    height, width = image.shape[:2]
                    x1, y1, x2, y2 = [int(round(value)) for value in region.bbox]
                    crop = image[max(0, y1):min(height, y2), max(0, x1):min(width, x2)]
                self.region_validation_results[region.region_id] = self.region_validator.validate(crop, region)
            validation = self.region_validation_results[region.region_id]
            # Explicit fail-open policy: provider unavailability is observational; a
            # completed semantic/heuristic rejection suppresses the candidate.
            if validation.verdict == "rejected":
                state.event_generated = True
                continue
            candidate = self._build_region_candidate(
                PendingRegionValidation(region, timestamp, len(people), absent, frame_data.source_type), frame_data)
            if candidate:
                candidates.append(candidate)
            state.event_generated = True
        if self.temporal_enabled:
            now = _timestamp(timestamp)
            for region_id, state in list(self.region_states.items()):
                pending = state.pending
                if pending is None or state.event_generated:
                    continue
                if now < _timestamp(pending.event_time) + self.temporal_post_seconds:
                    continue
                frames = self._temporal_window(pending.event_time)
                if not frames:
                    validation = VLMValidationResult(verdict="unavailable", reason="temporal:no_frames")
                else:
                    try:
                        validation = validate_temporal_compat(self.region_validator, frames,
                                                              pending.observation, pending.event_time)
                    except Exception:
                        validation = VLMValidationResult(verdict="unavailable",
                                                         reason="temporal:validator_error")
                self._cache_temporal_result(region_id, validation, {
                    "candidate_time": pending.event_time, "decision_time": timestamp,
                    "sampled_timestamps": [frame.captured_at for frame in frames],
                    "sampled_frame_count": len(frames),
                })
                state.event_generated = True
                state.pending = None
                if validation.verdict != "rejected":
                    candidate = self._build_region_candidate(pending, frame_data)
                    if candidate:
                        candidates.append(candidate)
                if region_id not in active_ids:
                    del self.region_states[region_id]
        self._submitted_regions = []
        return candidates

    def evaluate(self, tracks: List[TrackState], frame_data: FrameData) -> List[EventCandidate]:
        if self.candidate_source == "static_regions":
            return self._evaluate_regions(tracks, frame_data)
        candidates: List[EventCandidate] = []
        timestamp = frame_data.captured_at

        person_tracks = [t for t in tracks if t.class_name == "person"]
        object_tracks = [t for t in tracks if t.class_name in self.ALLOWED_CLASSES]
        active_obj_ids = {t.track_id for t in object_tracks}

        # 1. Update active object tracks detected by detector
        for obj in object_tracks:
            t_id = obj.track_id
            if t_id not in self.object_trackers:
                self.object_trackers[t_id] = ObjectStateTracker(
                    track_id=t_id,
                    first_frame_id=frame_data.frame_id,
                    class_name=obj.class_name,
                    stationary_seconds=self.stationary_seconds,
                    stationary_pixel_threshold=self.stationary_pixel_threshold,
                    owner_association_distance=self.owner_association_distance,
                    owner_absent_seconds=self.owner_absent_seconds,
                )

            tracker = self.object_trackers[t_id]
            state = tracker.update(obj.latest_bbox, timestamp, person_tracks, frame_data.frame_id)

        # 2. Update existing stationary object trackers even if missed by detector in current frame
        for t_id, tracker in list(self.object_trackers.items()):
            if t_id not in active_obj_ids and tracker.current_state != AbandonedObjectState.MOVING:
                state = tracker.update(None, timestamp, person_tracks, frame_data.frame_id)

            state = tracker.current_state
            if state == AbandonedObjectState.ABANDONED_CANDIDATE and not tracker.event_generated:
                dedupe_key = f"{self.camera_id}:{EventType.ABANDONED_OBJECT.value}:{t_id}"

                if self.dedupe_manager.should_emit(dedupe_key, timestamp):
                    candidate_id = f"{self.camera_id}-ABANDONED_OBJECT-obj{t_id}-{timestamp.replace(':', '').replace('-', '').replace('.', '')}"

                    stat_dur = calculate_duration_seconds(tracker.stationary_started_at, timestamp) if tracker.stationary_started_at else self.stationary_seconds
                    absent_dur = calculate_duration_seconds(tracker.owner_left_started_at, timestamp) if tracker.owner_left_started_at else self.owner_absent_seconds

                    bbox_to_use = tracker.last_known_bbox or [0, 0, 10, 10]
                    artifact = self.evidence_capture.capture_evidence(
                        frame_data=frame_data,
                        candidate_id=candidate_id,
                        polygon_pts=None,
                        bboxes=[bbox_to_use],
                    )

                    candidate = EventCandidate(
                        candidateId=candidate_id,
                        sourceEngine=SourceEngine.CV,
                        cameraId=self.camera_id,
                        zoneId=None,
                        sourceType=frame_data.source_type,
                        eventType=EventType.ABANDONED_OBJECT,
                        eventDetected=True,
                        detectedAt=timestamp,
                        firstSeenAt=tracker.stationary_started_at or timestamp,
                        lastSeenAt=timestamp,
                        confidence=0.90,
                        trackCount=1,
                        trackIds=[t_id],
                        observations=ObservationData(
                            personCount=len(person_tracks),
                            stationarySeconds=round(stat_dur, 2),
                            ownerAbsentSeconds=round(absent_dur, 2),
                        ),
                        modelVersion="yolo-v26m",
                        ruleVersion="abandoned-object-v1",
                        policyVersion=1,
                        artifact=artifact,
                    )

                    candidates.append(candidate)
                    self.dedupe_manager.record_emitted(dedupe_key, timestamp)
                    tracker.event_generated = True

        return candidates
