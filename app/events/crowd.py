from enum import Enum
from typing import List, Dict, Any, Optional
from app.common.enums import EventType, SourceEngine
from app.common.schemas import EventCandidate, ObservationData, FrameData
from app.common.geometry import is_point_in_polygon, scale_polygon_to_frame
from app.common.time_utils import calculate_duration_seconds, utc_now_iso
from app.events.base import BaseEventEngine
from app.events.dedupe import EventDedupeManager
from app.cv.track_store import TrackState
from app.cv.evidence import EvidenceCapture


class CrowdState(str, Enum):
    NORMAL = "NORMAL"
    THRESHOLD_PENDING = "THRESHOLD_PENDING"
    CROWD_ACTIVE = "CROWD_ACTIVE"
    RECOVERING = "RECOVERING"


class CrowdZoneStateTracker:
    def __init__(self, zone_id: str, count_threshold: int = 8, hold_seconds: float = 10.0, release_threshold: int = 5):
        self.zone_id = zone_id
        self.count_threshold = count_threshold
        self.hold_seconds = hold_seconds
        self.release_threshold = release_threshold

        self.current_state: CrowdState = CrowdState.NORMAL
        self.pending_started_at: Optional[str] = None
        self.event_generated: bool = False

    def update(self, current_count: int, timestamp: str) -> CrowdState:
        if self.current_state == CrowdState.NORMAL:
            if current_count >= self.count_threshold:
                self.current_state = CrowdState.THRESHOLD_PENDING
                self.pending_started_at = timestamp

        elif self.current_state == CrowdState.THRESHOLD_PENDING:
            if current_count >= self.count_threshold:
                duration = calculate_duration_seconds(self.pending_started_at, timestamp)
                if duration >= self.hold_seconds:
                    self.current_state = CrowdState.CROWD_ACTIVE
            else:
                # Count dropped below threshold before hold_seconds completed -> reset to NORMAL
                self.current_state = CrowdState.NORMAL
                self.pending_started_at = None

        elif self.current_state == CrowdState.CROWD_ACTIVE:
            if current_count <= self.release_threshold:
                self.current_state = CrowdState.RECOVERING

        elif self.current_state == CrowdState.RECOVERING:
            if current_count <= self.release_threshold:
                self.current_state = CrowdState.NORMAL
                self.pending_started_at = None
                self.event_generated = False
            elif current_count >= self.count_threshold:
                self.current_state = CrowdState.CROWD_ACTIVE
                self.event_generated = False  # Reset flag for re-triggering

        return self.current_state


class CrowdEventEngine(BaseEventEngine):
    def __init__(
        self,
        camera_id: str,
        zones_config: List[Dict[str, Any]],
        rules_config: Dict[str, Any],
        evidence_capture: Optional[EvidenceCapture] = None,
    ):
        self.camera_id = camera_id
        self.zones = [z for z in zones_config if z.get("camera_id") == camera_id and z.get("enabled", True)]

        crowd_rules = rules_config.get("crowd", {})
        self.count_threshold = int(crowd_rules.get("count_threshold", 8))
        self.hold_seconds = float(crowd_rules.get("hold_seconds", 10.0))
        self.release_threshold = int(crowd_rules.get("release_threshold", 5))
        self.cooldown_seconds = float(crowd_rules.get("cooldown_seconds", 60.0))

        self.zone_trackers: Dict[str, CrowdZoneStateTracker] = {}
        self.dedupe_manager = EventDedupeManager(cooldown_seconds=self.cooldown_seconds)
        self.evidence_capture = evidence_capture or EvidenceCapture()

    def evaluate(self, tracks: List[TrackState], frame_data: FrameData) -> List[EventCandidate]:
        candidates: List[EventCandidate] = []
        timestamp = frame_data.captured_at

        # Filter person tracks
        person_tracks = [t for t in tracks if t.class_name == "person"]

        img_h, img_w = (frame_data.image.shape[:2]) if frame_data.image is not None else (None, None)

        for zone in self.zones:
            z_id = zone["zone_id"]
            polygon_pts = scale_polygon_to_frame(zone["polygon"], frame_width=img_w, frame_height=img_h)

            if z_id not in self.zone_trackers:
                self.zone_trackers[z_id] = CrowdZoneStateTracker(
                    zone_id=z_id,
                    count_threshold=self.count_threshold,
                    hold_seconds=self.hold_seconds,
                    release_threshold=self.release_threshold,
                )

            tracker = self.zone_trackers[z_id]

            # Count distinct person tracks inside ROI polygon
            inside_tracks: List[TrackState] = []
            for track in person_tracks:
                foot_point = track.latest_foot_point
                if is_point_in_polygon(foot_point, polygon_pts):
                    inside_tracks.append(track)

            current_count = len(inside_tracks)
            prev_state = tracker.current_state
            new_state = tracker.update(current_count, timestamp)

            # Trigger event when transition THRESHOLD_PENDING -> CROWD_ACTIVE
            if new_state == CrowdState.CROWD_ACTIVE and not tracker.event_generated:
                dedupe_key = f"{self.camera_id}:{EventType.CROWD_THRESHOLD.value}:{z_id}"

                if self.dedupe_manager.should_emit(dedupe_key, timestamp):
                    candidate_id = f"{self.camera_id}-CROWD_THRESHOLD-{z_id}-{timestamp.replace(':', '').replace('-', '').replace('.', '')}"

                    inside_track_ids = [t.track_id for t in inside_tracks]
                    inside_bboxes = [t.latest_bbox for t in inside_tracks]

                    # Capture evidence frame
                    artifact = self.evidence_capture.capture_evidence(
                        frame_data=frame_data,
                        candidate_id=candidate_id,
                        polygon_pts=polygon_pts,
                        bboxes=inside_bboxes,
                    )

                    candidate = EventCandidate(
                        candidateId=candidate_id,
                        sourceEngine=SourceEngine.CV,
                        cameraId=self.camera_id,
                        zoneId=z_id,
                        sourceType=frame_data.source_type,
                        eventType=EventType.CROWD_THRESHOLD,
                        eventDetected=True,
                        detectedAt=timestamp,
                        firstSeenAt=tracker.pending_started_at or timestamp,
                        lastSeenAt=timestamp,
                        confidence=0.9,
                        trackCount=current_count,
                        trackIds=inside_track_ids,
                        observations=ObservationData(
                            personCount=current_count,
                            insideZone=True,
                        ),
                        modelVersion="deimv2-phase7a",
                        ruleVersion="crowd-rule-v1",
                        policyVersion=1,
                        artifact=artifact,
                    )

                    candidates.append(candidate)
                    self.dedupe_manager.record_emitted(dedupe_key, timestamp)
                    tracker.event_generated = True

        return candidates
