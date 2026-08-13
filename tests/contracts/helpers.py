from app.cv.contracts import (
    build_abandoned_event,
    build_crowd_event,
    build_intrusion_event,
)

TIME = "2026-08-10T16:30:25.125+07:00"


def intrusion(state="START", event_id="CAM01_IN_000001"):
    return build_intrusion_event(
        event_id=event_id, event_state=state, camera_id="CAM01", event_time=TIME,
        event_time_s=18.42, cv_confidence=0.95,
        persons=[{"track_id": 1000012, "bbox_xyxy": [420, 120, 490, 350]}],
        zone_id="RESTRICTED_01", inside_duration_s=1.2,
    )


def crowd(state="START", event_id="CAM01_CR_000001"):
    return build_crowd_event(
        event_id=event_id, event_state=state, camera_id="CAM01", event_time=TIME,
        event_time_s=53.0, cv_confidence=0.89,
        person_track_ids=[1001, 1002], threshold=2,
        above_threshold_duration_s=3.2,
    )


def abandoned(state="START", event_id="CAM01_AO_000001"):
    return build_abandoned_event(
        event_id=event_id, event_state=state, camera_id="CAM01", event_time=TIME,
        event_time_s=52.586, cv_confidence=0.91, physical_id="LUG_0001",
        source_track_ids=[2000004, 2000005],
        luggage_bbox_xyxy=[129.8, 324.4, 186.5, 377.6],
        owner_person_track_id=1000005, stationary_duration_s=8.4,
        owner_away_duration_s=5.1, owner_association_score=0.912,
    )
