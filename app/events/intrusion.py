from typing import List, Dict, Any, Optional
from app.common.enums import EventType, SourceEngine, IntrusionState
from app.common.schemas import EventCandidate, ObservationData, FrameData
from app.common.geometry import is_point_in_polygon, scale_polygon_to_frame
from app.common.time_utils import calculate_duration_seconds
from app.events.base import BaseEventEngine
from app.events.temporal_state import TrackIntrusionStateTracker
from app.events.dedupe import EventDedupeManager
from app.cv.track_store import TrackState
from app.cv.evidence import EvidenceCapture


class IntrusionEventEngine(BaseEventEngine):
    def __init__(
        self,
        camera_id: str,
        zones_config: List[Dict[str, Any]],
        rules_config: Dict[str, Any],
        evidence_capture: Optional[EvidenceCapture] = None,
    ):
        self.camera_id = camera_id
        self.zones = [z for z in zones_config if z.get("camera_id") == camera_id and z.get("enabled", True)]
        
        intrusion_rules = rules_config.get("intrusion", {})
        self.dwell_seconds = float(intrusion_rules.get("dwell_seconds", 1.0))
        self.exit_grace_seconds = float(intrusion_rules.get("exit_grace_seconds", 0.5))
        self.cooldown_seconds = float(intrusion_rules.get("cooldown_seconds", 30))

        self.state_trackers: Dict[int, Dict[str, TrackIntrusionStateTracker]] = {}  # track_id -> {zone_id: Tracker}
        self.dedupe_manager = EventDedupeManager(cooldown_seconds=self.cooldown_seconds)
        self.evidence_capture = evidence_capture or EvidenceCapture()

    def evaluate(self, tracks: List[TrackState], frame_data: FrameData) -> List[EventCandidate]:
        candidates: List[EventCandidate] = []
        timestamp = frame_data.captured_at
        img_h, img_w = (frame_data.image.shape[:2]) if frame_data.image is not None else (None, None)

        for track in tracks:
            if track.class_name != "person":
                continue

            t_id = track.track_id
            foot_x, foot_y = track.latest_foot_point

            if t_id not in self.state_trackers:
                self.state_trackers[t_id] = {}

            for zone in self.zones:
                z_id = zone["zone_id"]
                polygon_pts = scale_polygon_to_frame(zone["polygon"], frame_width=img_w, frame_height=img_h)

                if z_id not in self.state_trackers[t_id]:
                    self.state_trackers[t_id][z_id] = TrackIntrusionStateTracker(
                        track_id=t_id, dwell_threshold=self.dwell_seconds, exit_grace_seconds=self.exit_grace_seconds
                    )

                tracker = self.state_trackers[t_id][z_id]
                inside = is_point_in_polygon((foot_x, foot_y), polygon_pts)

                if inside:
                    prev_state = tracker.current_state
                    new_state = tracker.update_inside(timestamp)

                    # Trigger candidate ONLY on transition to INTRUSION_ACTIVE
                    if new_state == IntrusionState.INTRUSION_ACTIVE and not tracker.event_generated:
                        dedupe_key = self.dedupe_manager.generate_dedupe_key(
                            self.camera_id, EventType.ZONE_INTRUSION.value, z_id, t_id
                        )

                        if self.dedupe_manager.should_emit(dedupe_key, timestamp):
                            candidate_id = self.dedupe_manager.generate_candidate_id(
                                self.camera_id, EventType.ZONE_INTRUSION.value, z_id, t_id, timestamp
                            )

                            dwell_duration = calculate_duration_seconds(tracker.entered_zone_at, timestamp)

                            # Capture evidence frame
                            artifact = self.evidence_capture.capture_evidence(
                                frame_data=frame_data,
                                candidate_id=candidate_id,
                                polygon_pts=polygon_pts,
                                bboxes=[track.latest_bbox],
                            )

                            candidate = EventCandidate(
                                candidateId=candidate_id,
                                sourceEngine=SourceEngine.CV,
                                cameraId=self.camera_id,
                                zoneId=z_id,
                                sourceType=frame_data.source_type,
                                eventType=EventType.ZONE_INTRUSION,
                                eventDetected=True,
                                detectedAt=timestamp,
                                firstSeenAt=tracker.entered_zone_at or timestamp,
                                lastSeenAt=timestamp,
                                confidence=track.confidence,
                                trackCount=1,
                                trackIds=[t_id],
                                bbox=list(track.latest_bbox),
                                observations=ObservationData(
                                    personCount=1,
                                    dwellSeconds=round(dwell_duration, 2),
                                    insideZone=True,
                                ),
                                modelVersion="deimv2-phase7a",
                                ruleVersion="intrusion-rule-v1",
                                policyVersion=1,
                                artifact=artifact,
                            )

                            candidates.append(candidate)
                            self.dedupe_manager.record_emitted(dedupe_key, timestamp)
                            tracker.event_generated = True

                else:
                    tracker.update_outside(timestamp)

        return candidates
