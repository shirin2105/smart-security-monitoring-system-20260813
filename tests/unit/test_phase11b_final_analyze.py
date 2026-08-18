import pytest

from scripts.phase11b_final_analyze import negative_metrics, require_absent, terminal_exit_code, write_new


def test_negative_metrics_uses_completed_run_coverage():
    result = negative_metrics({"a", "b"}, {"a", "b"}, [], 3600)
    assert result["pass"] is True
    assert result["completed_clips"] == 2
    with pytest.raises(ValueError):
        negative_metrics({"a", "b"}, {"a"}, [], 3600)


def test_negative_metrics_fails_on_abandoned_start_and_bad_schema():
    with pytest.raises(ValueError):
        negative_metrics({"a"}, {"a"}, [{"camera_id": "a"}], 1)


def test_unresolved_status_is_fail_closed():
    assert terminal_exit_code("READY_FOR_PHASE12", True) == 0
    assert terminal_exit_code("ROI_POLICY_UNRESOLVED", True) == 2
    assert terminal_exit_code("READY_FOR_PHASE12", False) == 1


def test_analysis_outputs_are_create_only(tmp_path):
    target = tmp_path / "result.json"
    write_new(target, "{}")
    with pytest.raises(FileExistsError):
        write_new(target, "{}")
    with pytest.raises(FileExistsError):
        require_absent([target, tmp_path / "missing"])
