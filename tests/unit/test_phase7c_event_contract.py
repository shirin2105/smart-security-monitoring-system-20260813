from app.cv.phase7c_tracking.event_contract import AbandonedObjectCandidate


def payload():
    return {
        "event_id": "AO_0001",
        "physical_id": "LUG_0001",
        "source_track_ids": [2_000_001, 2_000_002],
        "owner_person_track_id": 1_000_001,
        "stationary_start_s": 5.0,
        "stationary_confirmed_s": 8.0,
        "owner_last_near_s": 6.0,
        "candidate_time_s": 11.0,
        "owner_away_s": 5.0,
        "association_score": 0.8,
        "bbox_xyxy": [100.0, 100.0, 130.0, 140.0],
        "center_xy": [115.0, 120.0],
        "status": "ABANDONED_OBJECT_CANDIDATE",
    }


def test_candidate_round_trip_preserves_audit_fields():
    raw = payload()
    assert AbandonedObjectCandidate.from_mapping(raw).to_dict() == raw


def test_candidate_rejects_confirmed_alarm_status():
    raw = payload()
    raw["status"] = "ABANDONED_OBJECT"
    try:
        AbandonedObjectCandidate.from_mapping(raw)
    except ValueError as error:
        assert "candidates only" in str(error)
    else:
        raise AssertionError("confirmed alarm status was accepted")


def test_candidate_rejects_inconsistent_owner_away_duration():
    raw = payload()
    raw["owner_away_s"] = 4.0
    try:
        AbandonedObjectCandidate.from_mapping(raw)
    except ValueError as error:
        assert "owner_away_s" in str(error)
    else:
        raise AssertionError("inconsistent owner-away duration was accepted")
