"""Phase 11A GT validator tests."""

from __future__ import annotations

import pytest

from app.evaluation.phase11_schema import GroundTruthEvent
from app.evaluation.phase11a_validate import GroundTruthValidator, GTIssue, load_review_status


def _manifest(clip_ids=("a", "b")):
    return {"clips": [{"clip_id": c, "camera_id": c, "duration_s": 50.0} for c in clip_ids]}


def _gt(clip="a", event_id="gt1", event_type="ZONE_INTRUSION", start=0, trigger=5, end=10):
    return GroundTruthEvent(clip, clip, event_id, event_type, start, trigger, end)


def _validator(manifest=None, review=None, durations=None, zones=None):
    return GroundTruthValidator(
        manifest or _manifest(),
        review_status=review or {},
        clip_durations=durations or {},
        zone_by_clip=zones or {},
    )


def test_valid_event_passes():
    usable, issues = _validator().validate([_gt()])
    assert len(usable) == 1
    assert all(i.severity != "error" for i in issues)


def test_invalid_event_type_rejected():
    bad = GroundTruthEvent("a", "a", "gt1", "NOT_A_TYPE", 0, 5, 10)
    usable, issues = _validator().validate([bad])
    assert len(usable) == 0
    assert any("invalid event_type" in i.message for i in issues)


def test_clip_not_in_manifest_rejected():
    _, issues = _validator().validate([_gt(clip="zzz")])
    assert any("not in manifest" in i.message for i in issues)


def test_camera_mismatch_rejected():
    bad = GroundTruthEvent("a", "other", "gt1", "ZONE_INTRUSION", 0, 5, 10)
    _, issues = _validator().validate([bad])
    assert any("camera_id mismatch" in i.message for i in issues)


def test_timing_order_violation_rejected():
    bad = GroundTruthEvent("a", "a", "gt1", "ZONE_INTRUSION", 0, 10, 5)
    _, issues = _validator().validate([bad])
    assert any("timing order" in i.message for i in issues)


def test_duplicate_event_id_rejected():
    _, issues = _validator().validate([_gt(), _gt()])
    assert any("duplicate" in i.message.lower() for i in issues)


def test_end_beyond_clip_duration_warns():
    validator = _validator(durations={"a": 8.0})
    _, issues = validator.validate([_gt(end=10)])
    assert any("exceeds clip duration" in i.message for i in issues)


def test_unknown_zone_rejected():
    validator = _validator(zones={"a": ["CENTRAL_ROI"]})
    gt = GroundTruthEvent("a", "a", "gt1", "ZONE_INTRUSION", 0, 5, 10, zone_id="WRONG")
    _, issues = validator.validate([gt])
    assert any("zone" in i.message for i in issues)


def test_excluded_clip_skipped_from_benchmark():
    review = {"a": {"review_status": "EXCLUDED", "positive_negative": "negative"}}
    validator = _validator(review=review)
    usable, issues = validator.validate([_gt()])
    assert len(usable) == 0
    assert any("EXCLUDED" in i.message for i in issues)


def test_unreviewed_clip_warns_but_included():
    validator = _validator()  # default no review status -> UNREVIEWED
    usable, issues = validator.validate([_gt()])
    assert len(usable) == 1
    assert any("UNREVIEWED" in i.message for i in issues)


def test_invalid_review_status_detected():
    from app.evaluation.phase11a_validate import validate_review_statuses

    issues = validate_review_statuses({"a": {"review_status": "BOGUS"}})
    assert any("invalid review_status" in i.message for i in issues)


def test_load_review_status(tmp_path):
    csv_path = tmp_path / "clip_review_status.csv"
    csv_path.write_text("clip_id,event_target,review_status,positive_negative\n"
                        "a,intrusion,REVIEWED,positive\n"
                        "b,,EXCLUDED,negative\n", encoding="utf-8")
    statuses = load_review_status(csv_path)
    assert statuses["a"]["review_status"] == "REVIEWED"
    assert statuses["b"]["review_status"] == "EXCLUDED"
