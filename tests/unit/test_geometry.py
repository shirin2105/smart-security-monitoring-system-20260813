import pytest
from app.common.geometry import get_foot_point, is_point_in_polygon


def test_get_foot_point():
    bbox = [100.0, 200.0, 300.0, 500.0]
    foot_x, foot_y = get_foot_point(bbox)
    assert foot_x == 200.0
    assert foot_y == 500.0


def test_is_point_in_polygon():
    polygon = [
        [0.0, 0.0],
        [100.0, 0.0],
        [100.0, 100.0],
        [0.0, 100.0],
    ]
    # Inside point
    assert is_point_in_polygon((50.0, 50.0), polygon) is True
    # Outside point
    assert is_point_in_polygon((150.0, 50.0), polygon) is False
