"""Phase 11 evaluator tests (the 13 required evaluation checks)."""

from __future__ import annotations

import json

import pytest

from app.evaluation.phase11_evaluator import (
    evaluate_benchmark,
    load_predictions_from_cv_event,
)
from app.evaluation.phase11_schema import (
    GroundTruthEvent,
    PredictedEvent,
    collapse_lifecycles,
    prediction_from_cv_event,
)


def _gt(clip="c", cam="c", event_id="gt1", event_type="ZONE_INTRUSION",
        start=0.0, trigger=10.0, end=15.0):
    return GroundTruthEvent(clip, cam, event_id, event_type, start, trigger, end)


def _pred(clip="c", cam="c", event_id="p1", event_type="ZONE_INTRUSION", t=10.5):
    return PredictedEvent(clip, cam, event_id, event_type, t)


# 1. perfect match
def test_perfect_match():
    result = evaluate_benchmark([_gt()], [_pred()], total_video_hours=1.0)
    assert result["overall_micro"]["tp"] == 1
    assert result["overall_micro"]["precision"] == 1.0
    assert result["overall_micro"]["recall"] == 1.0


# 2. no predictions -> all FN
def test_no_predictions():
    result = evaluate_benchmark([_gt()], [], total_video_hours=1.0)
    assert result["overall_micro"]["fn"] == 1
    assert result["overall_micro"]["recall"] == 0.0


# 3. no GT -> all FP
def test_no_ground_truth():
    result = evaluate_benchmark([], [_pred()], total_video_hours=1.0)
    assert result["overall_micro"]["fp"] == 1
    assert result["overall_micro"]["precision"] == 0.0


# 4. wrong event type is not matched
def test_wrong_event_type_not_matched():
    gt = _gt(event_type="ZONE_INTRUSION")
    pred = _pred(event_type="CROWD_THRESHOLD")
    result = evaluate_benchmark([gt], [pred], total_video_hours=1.0)
    assert result["by_event"]["ZONE_INTRUSION"]["fn"] == 1
    assert result["by_event"]["CROWD_THRESHOLD"]["fp"] == 1


# 5. tolerance boundary is inclusive
def test_tolerance_boundary_inclusive():
    gt = _gt(trigger=10.0, end=15.0)
    # intrusion tolerance 2s; pred exactly at end + 2 = 17 matches
    pred = _pred(t=17.0)
    result = evaluate_benchmark([gt], [pred], total_video_hours=1.0)
    assert result["overall_micro"]["tp"] == 1


# 6. one prediction cannot match two GT
def test_one_prediction_cannot_match_two_gt():
    gt1 = _gt(event_id="gt1", trigger=10.0, end=15.0)
    gt2 = _gt(event_id="gt2", trigger=11.0, end=16.0)
    pred = _pred(t=11.5)
    result = evaluate_benchmark([gt1, gt2], [pred], total_video_hours=1.0)
    assert result["overall_micro"]["tp"] == 1
    assert result["overall_micro"]["fn"] == 1  # the other GT is missed


# 7. duplicate prediction within a matched GT window is a duplicate
def test_duplicate_prediction():
    gt = _gt()
    pred1 = _pred(event_id="p1", t=10.5)
    pred2 = _pred(event_id="p2", t=11.0)
    result = evaluate_benchmark([gt], [pred1, pred2], total_video_hours=1.0)
    assert result["overall_micro"]["tp"] == 1
    assert result["overall_micro"]["duplicates"] == 1
    assert result["overall_micro"]["duplicate_rate"] == pytest.approx(0.5)


# 8. false alarms per hour
def test_false_alarms_per_hour():
    gt = _gt()
    pred = _pred(event_id="p1", event_type="CROWD_THRESHOLD")  # wrong type -> FP
    result = evaluate_benchmark([gt], [pred], total_video_hours=2.0)
    assert result["overall_micro"]["false_alarms_per_hour"] == pytest.approx(0.5)


# 9. early alert is matched but flagged (negative delay)
def test_early_alert():
    gt = _gt(trigger=10.0, end=15.0)
    pred = _pred(t=9.0)  # 1s early, within 2s tolerance
    result = evaluate_benchmark([gt], [pred], total_video_hours=1.0)
    assert result["overall_micro"]["tp"] == 1
    match = result["matches"][0]
    assert match["error_kind"] == "EARLY_ALERT"
    assert match["delay_s"] < 0


# 10. late alert is matched but flagged (within end+tolerance)
def test_late_alert():
    gt = _gt(trigger=10.0, end=12.0)
    pred = _pred(t=13.0)  # 3s after trigger, > tolerance 2, but <= end+2=14
    result = evaluate_benchmark([gt], [pred], total_video_hours=1.0)
    assert result["overall_micro"]["tp"] == 1
    assert result["matches"][0]["error_kind"] == "LATE_ALERT"


# 11. lifecycle collapse: START/UPDATE/END -> one instance
def test_lifecycle_collapse():
    def cv_event(event_id, state, t):
        return {
            "schema_version": "cv-event-v1", "event_id": event_id,
            "event_type": "ZONE_INTRUSION", "event_state": state,
            "camera_id": "c", "event_time": "t", "event_time_s": t,
            "cv_confidence": 0.9, "objects": {}, "evidence": {},
            "spatial": {}, "media": {}, "diagnostics": {},
        }
    raw = [cv_event("life-1", "START", 5.0), cv_event("life-1", "UPDATE", 6.0),
           cv_event("life-1", "END", 7.0)]
    instances = collapse_lifecycles([prediction_from_cv_event(r) for r in raw])
    assert len(instances) == 1
    assert instances[0].event_time_s == 5.0
    assert set(instances[0].lifecycle_states) == {"START", "UPDATE", "END"}


# 11b. load_predictions_from_cv_event collapses a real jsonl
def test_load_predictions_collapses(tmp_path):
    path = tmp_path / "preds.jsonl"
    records = [
        {"schema_version": "cv-event-v1", "event_id": "e1", "event_type": "ZONE_INTRUSION",
         "event_state": "START", "camera_id": "c", "event_time": "t", "event_time_s": 5.0,
         "cv_confidence": 0.9, "objects": {}, "evidence": {}, "spatial": {}, "media": {}, "diagnostics": {}},
        {"schema_version": "cv-event-v1", "event_id": "e1", "event_type": "ZONE_INTRUSION",
         "event_state": "END", "camera_id": "c", "event_time": "t", "event_time_s": 7.0,
         "cv_confidence": 0.9, "objects": {}, "evidence": {}, "spatial": {}, "media": {}, "diagnostics": {}},
    ]
    path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    preds = load_predictions_from_cv_event(path)
    assert len(preds) == 1
    assert preds[0].event_time_s == 5.0


# 12. micro vs macro aggregation
def test_micro_macro_aggregation():
    gts = [
        _gt(event_id="a", event_type="ZONE_INTRUSION", trigger=10, end=15),
        _gt(event_id="b", event_type="CROWD_THRESHOLD", trigger=10, end=15),
        _gt(event_id="c", event_type="ABANDONED_OBJECT", trigger=10, end=15),
    ]
    preds = [
        _pred(event_id="p1", event_type="ZONE_INTRUSION", t=10.5),
        _pred(event_id="p2", event_type="CROWD_THRESHOLD", t=10.5),
        _pred(event_id="p3", event_type="ABANDONED_OBJECT", t=10.5),
    ]
    result = evaluate_benchmark(gts, preds, total_video_hours=1.0)
    # all matched: micro precision=recall=f1=1
    assert result["overall_micro"]["precision"] == 1.0
    # each per-event f1=1 -> macro mean f1 = 1
    assert result["overall_macro"]["f1"] == pytest.approx(1.0)


# 13. deterministic output
def test_deterministic_output():
    gts = [_gt(event_id=f"g{i}", trigger=10, end=15) for i in range(5)]
    preds = [_pred(event_id=f"p{i}", t=10.5 + 0.1 * i) for i in range(4)]
    first = evaluate_benchmark(gts, preds, total_video_hours=1.0)
    second = evaluate_benchmark(gts, preds, total_video_hours=1.0)
    assert json.dumps(first["matches"], sort_keys=True) == json.dumps(second["matches"], sort_keys=True)
    assert first["overall_micro"] == second["overall_micro"]


# 12b. macro aggregation includes a zero-TP event type (honest 0 contribution)
def test_macro_includes_zero_tp_event_type():
    gts = [
        _gt(event_id="a", event_type="ZONE_INTRUSION", trigger=10, end=15),
        _gt(event_id="b", event_type="ABANDONED_OBJECT", trigger=10, end=15),
    ]
    preds = [_pred(event_id="p1", event_type="ZONE_INTRUSION", t=10.5)]  # abandoned never predicted
    result = evaluate_benchmark(gts, preds, total_video_hours=1.0)
    # ZONE_F1=1.0, ABANDONED_F1=0.0 -> macro f1 = 0.5
    assert result["overall_macro"]["f1"] == pytest.approx(0.5)


# 8b. FA/h counts FP (not duplicates) across the whole corpus
def test_fa_per_hour_uses_total_fp():
    gt = _gt(trigger=10, end=15)
    preds = [_pred(event_id="p1", t=10.5), _pred(event_id="p2", t=11.0)]  # 1 TP + 1 duplicate
    result = evaluate_benchmark([gt], preds, total_video_hours=2.0)
    assert result["overall_micro"]["duplicates"] == 1
    assert result["overall_micro"]["false_alarms_per_hour"] == 0.0  # duplicates are not FA


# zone-incompatible prediction is not matched
def test_zone_incompatible_prediction_not_matched():
    gt = GroundTruthEvent("c", "c", "gt1", "ZONE_INTRUSION", 0, 10, 15, zone_id="ROI_A")
    pred = PredictedEvent("c", "c", "p1", "ZONE_INTRUSION", 10.5, evidence={"zone_id": "ROI_B"})
    result = evaluate_benchmark([gt], [pred], total_video_hours=1.0)
    assert result["overall_micro"]["tp"] == 0
    assert result["overall_micro"]["fn"] == 1


# zero duration is rejected
def test_zero_video_hours_rejected():
    with pytest.raises(ValueError):
        evaluate_benchmark([_gt()], [_pred()], total_video_hours=0.0)
