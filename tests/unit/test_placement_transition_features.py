from kaggle_pipeline.phase7c_kernel.placement_transition import placement_transition_features


def observation(time_s, bag_x, person_x, person_y=100.0):
    return {
        "timestamp_s": time_s,
        "bag_center": [bag_x, 120.0],
        "person_center": [person_x, person_y],
        "person_bbox": [person_x - 30.0, person_y - 50.0, person_x + 30.0, person_y + 50.0],
    }


def test_co_moving_owner_has_placement_transition_evidence():
    rows = [observation(i * 0.2, 100 + i * 6, 100 + i * 6) for i in range(6)]

    result = placement_transition_features(rows)

    assert result["evidence_sufficient"] is True
    assert result["placement_predicate_passed"] is True


def test_passerby_crossing_stationary_bag_fails_placement_predicate():
    rows = [observation(i * 0.2, 120, 80 + i * 16) for i in range(6)]

    result = placement_transition_features(rows)

    assert result["evidence_sufficient"] is True
    assert result["placement_predicate_passed"] is False


def test_opposite_direction_crossing_fails_placement_predicate():
    rows = [observation(i * 0.2, 100 + i * 5, 150 - i * 5) for i in range(6)]

    assert placement_transition_features(rows)["placement_predicate_passed"] is False


def test_sparse_or_duplicate_timestamps_fail_closed():
    sparse = [observation(0.0, 100, 100), observation(0.8, 110, 110)]
    duplicate = [observation(0.0, 100 + i, 100 + i) for i in range(4)]

    assert placement_transition_features(sparse)["evidence_sufficient"] is False
    assert placement_transition_features(duplicate)["evidence_sufficient"] is False


def test_translation_and_scale_do_not_change_decision():
    base = [observation(i * 0.2, 100 + i * 6, 100 + i * 6) for i in range(6)]
    shifted = []
    for item in base:
        shifted.append({
            "timestamp_s": item["timestamp_s"],
            "bag_center": [2 * item["bag_center"][0] + 300, 2 * item["bag_center"][1]],
            "person_center": [2 * item["person_center"][0] + 300, 2 * item["person_center"][1]],
            "person_bbox": [2 * value + (300 if index % 2 == 0 else 0)
                            for index, value in enumerate(item["person_bbox"])],
        })

    assert placement_transition_features(base)["placement_predicate_passed"] is True
    assert placement_transition_features(shifted)["placement_predicate_passed"] is True
