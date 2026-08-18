from scripts.owner_association_v2_analyze import abandoned_starts, best_candidate


def test_abandoned_starts_filters_event_type_and_state():
    rows = [{"event_type": "ABANDONED_OBJECT", "event_state": "START"},
            {"event_type": "ABANDONED_OBJECT", "event_state": "END"},
            {"event_type": "ZONE_INTRUSION", "event_state": "START"}]
    assert abandoned_starts(rows) == [rows[0]]


def test_best_candidate_is_deterministic_and_requires_eligibility():
    row = {
        "owner_candidate_scores": [0.8, 0.8, 0.9],
        "owner_candidate_selected": [False, True, False],
        "owner_candidate_eligible": [True, True, False],
        "owner_candidate_person_ids": [9, 3, 1],
        "owner_candidate_min_association_scores": [0.6] * 3,
        "owner_candidate_min_distances_px": [1.0] * 3,
        "owner_candidate_min_distances": [0.1] * 3,
        "owner_candidate_inside_ratios": [0.0] * 3,
        "owner_candidate_near_ratios": [0.5] * 3,
        "owner_candidate_overlap_seconds": [1.0] * 3,
        "owner_candidate_temporal_overlap_ratios": [1.0] * 3,
        "owner_candidate_score_components": [{"inside": 0, "near": .1, "overlap": .1}] * 3,
        "owner_candidate_track_fragmented": [False] * 3,
    }
    assert best_candidate([row])["track"] == 3
    assert best_candidate([row], selected_only=True)["track"] == 3
