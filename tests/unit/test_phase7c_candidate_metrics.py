from app.evaluation.phase7c_candidate_metrics import evaluate_phase7c_candidates


def event(event_id="AO_0001", candidate_time=11.0):
    return {
        "event_id": event_id,
        "physical_id": "LUG_0001",
        "source_track_ids": [2_000_001],
        "owner_person_track_id": 1_000_001,
        "stationary_start_s": 5.0,
        "stationary_confirmed_s": 8.0,
        "owner_last_near_s": 6.0,
        "candidate_time_s": candidate_time,
        "owner_away_s": candidate_time - 6.0,
        "association_score": 0.8,
        "bbox_xyxy": [100.0, 100.0, 130.0, 140.0],
        "center_xy": [115.0, 120.0],
        "status": "ABANDONED_OBJECT_CANDIDATE",
    }


def manifest(labels=None):
    return {
        "video_id": "video-1",
        "camera_id": "camera-1",
        "processed_seconds": 1800.0,
        "labels": labels or [],
        "tolerance": {"early_s": 0.0, "late_s": 2.0},
    }


def test_metrics_report_precision_recall_false_rate_and_delay():
    labels = [{"label_id": "label-1", "start_s": 10.0, "end_s": 10.0}]
    result = evaluate_phase7c_candidates([event()], manifest(labels))
    assert result["evaluation_scope"] == "ABANDONED_OBJECT_CANDIDATE_ONLY"
    assert result["confirmed_alarm_metrics"] is False
    assert result["overall"]["precision"] == 1.0
    assert result["overall"]["recall"] == 1.0
    assert result["overall"]["false_candidates_per_video_hour"] == 0.0
    assert result["overall"]["false_alarms_per_video_hour"] is None
    assert result["overall"]["matched_delay"]["mean_seconds"] == 1.0


def test_duplicate_candidate_is_false_positive():
    labels = [{"label_id": "label-1", "start_s": 10.0, "end_s": 10.0}]
    result = evaluate_phase7c_candidates(
        [event("AO_0001", 10.5), event("AO_0002", 11.0)], manifest(labels)
    )
    assert (result["overall"]["tp"], result["overall"]["fp"]) == (1, 1)
    assert result["overall"]["false_candidates_per_video_hour"] == 2.0
