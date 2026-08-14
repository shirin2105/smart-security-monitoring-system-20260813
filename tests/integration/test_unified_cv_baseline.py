from app.cv.contracts import (
    CVEvent,
    build_abandoned_event,
    build_crowd_event,
    build_intrusion_event,
)
from app.cv.contracts.validation import EVENT_TYPES, validate_event


def common():
    return dict(event_id="event-1", event_state="START", camera_id="cam",
                event_time="2026-01-01T00:00:00Z", event_time_s=0,
                cv_confidence=0.9)


def test_exactly_three_contract_builders_round_trip():
    events = [
        build_intrusion_event(**common(), persons=[{"track_id": 1,
            "bbox_xyxy": [0, 0, 1, 1]}], zone_id="z", inside_duration_s=2),
        build_crowd_event(**common(), person_track_ids=[1, 2], threshold=2,
                          above_threshold_duration_s=3),
        build_abandoned_event(**common(), physical_id="LUG_1", source_track_ids=[3],
            luggage_bbox_xyxy=[0, 0, 1, 1], owner_person_track_id=1,
            stationary_duration_s=3, owner_away_duration_s=5,
            owner_association_score=0.8),
    ]
    assert {event.event_type for event in events} == EVENT_TYPES
    for event in events:
        validate_event(event)
        assert CVEvent.from_json(event.to_json()) == event
