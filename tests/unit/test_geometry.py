import pytest
from app.common.geometry import get_foot_point, is_point_in_polygon, scale_polygon_to_frame


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


def test_scale_polygon_to_frame():
    # 1. 1280x720 reference polygon scaled to 768x432 (Camera 2)
    poly_1280 = [[0, 0], [1280, 0], [1280, 720], [0, 720]]
    scaled = scale_polygon_to_frame(poly_1280, frame_width=768, frame_height=432)
    assert scaled == [[0.0, 0.0], [768.0, 0.0], [768.0, 432.0], [0.0, 432.0]]

    # 2. Normalized polygon [0..1]
    poly_norm = [[0.0, 0.0], [0.5, 0.0], [0.5, 0.5], [0.0, 0.5]]
    scaled_norm = scale_polygon_to_frame(poly_norm, frame_width=640, frame_height=480)
    assert scaled_norm == [[0.0, 0.0], [320.0, 0.0], [320.0, 240.0], [0.0, 240.0]]

    # 3. None dimensions or same dimensions returns polygon as is
    assert scale_polygon_to_frame(poly_1280, None, None) == poly_1280
    assert scale_polygon_to_frame(poly_1280, 1280, 720) == poly_1280
