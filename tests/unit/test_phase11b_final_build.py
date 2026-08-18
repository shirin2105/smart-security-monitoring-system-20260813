import json

import pytest

from scripts.phase11b_final_build import CLIPS, generic_negative_ids, require_absent, validate_decisions


def test_generic_negative_manifest_selection():
    manifest = {"clips": [{"clip_id": "n", "scenario_tags": ["abandoned_negative"]},
                           {"clip_id": "p", "scenario_tags": ["abandoned_positive"]}]}
    assert generic_negative_ids(manifest) == ["n"]


def test_adjudication_requires_exact_clips_and_excludes_ambiguous():
    rows = [{"clip_id": clip, "adjudication_status": "AMBIGUOUS_NEEDS_HUMAN", "is_in_policy": False}
            for clip in CLIPS]
    validate_decisions(rows)
    rows[0]["is_in_policy"] = True
    with pytest.raises(ValueError):
        validate_decisions(rows)


def test_adjudication_rejects_missing_or_invalid_status():
    rows = [{"clip_id": clip, "adjudication_status": "AMBIGUOUS_NEEDS_HUMAN", "is_in_policy": False}
            for clip in CLIPS]
    with pytest.raises(ValueError):
        validate_decisions(rows[:-1])
    rows[0]["adjudication_status"] = "MADE_UP"
    with pytest.raises(ValueError):
        validate_decisions(rows)


def test_adjudication_status_fields_must_agree():
    rows = [{"clip_id": clip, "adjudication_status": "AMBIGUOUS_NEEDS_HUMAN",
             "is_in_policy": False, "roi_change_required": False} for clip in CLIPS]
    rows[0].update(adjudication_status="IN_POLICY_POSITIVE", is_in_policy=False)
    with pytest.raises(ValueError):
        validate_decisions(rows)
    rows[0].update(adjudication_status="OUT_OF_POLICY_GT", is_in_policy=False, roi_change_required=True)
    with pytest.raises(ValueError):
        validate_decisions(rows)


def test_final_evidence_is_create_only(tmp_path):
    target = tmp_path / "evidence.json"
    require_absent([target])
    target.write_text("{}")
    with pytest.raises(FileExistsError):
        require_absent([target])
