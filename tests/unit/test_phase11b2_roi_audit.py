import pytest

from scripts.phase11_infer import CENTRAL_ROI, _phase7c_config, zones_for
from scripts.phase11b2_roi_audit import bbox_points, resolve_roi_points, restore_letterbox_bbox
from scripts.phase11b2_analyze import negative_gate
from kaggle_pipeline.phase7c_kernel.phase7c_core import point_in_polygon


def test_normalized_and_pixel_roi_resolution():
    assert resolve_roi_points([[0, 0], [1, 0], [1, 1]], "normalized", 384, 288) == [[0, 0], [384, 0], [384, 288]]
    assert resolve_roi_points([[1, 2], [3, 4], [5, 6]], "pixel", 384, 288) == [[1, 2], [3, 4], [5, 6]]


def test_inside_outside_and_boundary_are_deterministic():
    polygon = [[0, 0], [10, 0], [10, 10], [0, 10]]
    assert point_in_polygon((5, 5), polygon)
    assert not point_in_polygon((15, 5), polygon)
    assert point_in_polygon((0, 5), polygon) == point_in_polygon((0, 5), polygon)


def test_center_bottom_center_and_letterbox_restoration():
    assert bbox_points([10, 20, 30, 50]) == ([20, 35], [20, 50])
    assert restore_letterbox_bbox([30, 50, 70, 90], 2, 10, 10) == [10, 20, 30, 40]


def test_invalid_roi_is_rejected():
    with pytest.raises(ValueError):
        resolve_roi_points([[0, 0], [1, 1]], "pixel", 384, 288)
    with pytest.raises(ValueError):
        resolve_roi_points([[0, 0], [2, 0], [1, 1]], "normalized", 384, 288)


def test_frozen_default_and_diagnostic_event_specific_roi(monkeypatch):
    assert zones_for("clip")[0]["polygon"] == CENTRAL_ROI
    assert _phase7c_config()["valid_floor_roi_polygon"] == CENTRAL_ROI
    monkeypatch.setenv("PHASE11B2_DISABLE_ABANDONED_ROI", "1")
    assert _phase7c_config()["valid_floor_roi_polygon"] is None


@pytest.mark.parametrize(
    ("expected", "observed", "starts", "allowed"),
    [
        ({"a", "b"}, {"a", "b"}, [], True),
        ({"a", "b"}, {"a"}, [], False),
        ({"a"}, {"a", "b"}, [], False),
        ({"a"}, {"a"}, [{"event_state": "START"}], False),
    ],
)
def test_negative_gate_fails_closed(expected, observed, starts, allowed):
    assert negative_gate(expected, observed, starts) is allowed
