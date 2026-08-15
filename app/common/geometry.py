from typing import List, Tuple, Optional

try:
    from shapely.geometry import Point, Polygon
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False


def get_foot_point(bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
    """
    Calculate foot point from bounding box [x1, y1, x2, y2].
    foot_x = (x1 + x2) / 2
    foot_y = y2
    """
    x1, y1, x2, y2 = bbox
    foot_x = (x1 + x2) / 2.0
    foot_y = float(y2)
    return foot_x, foot_y


def scale_polygon_to_frame(
    polygon_pts: List[List[float]],
    frame_width: Optional[int] = None,
    frame_height: Optional[int] = None,
    reference_width: float = 1280.0,
    reference_height: float = 720.0,
) -> List[List[float]]:
    """
    Scales polygon coordinates to match current frame dimensions.
    Handles:
    1. Normalized coordinates [0.0, 1.0] -> scales to (frame_width, frame_height).
    2. Reference canvas coordinates (e.g. 1280x720 from UI) -> scales to (frame_width, frame_height).
    3. If frame dimensions match reference or are None -> returns polygon_pts unchanged.
    """
    if not polygon_pts or frame_width is None or frame_height is None:
        return polygon_pts

    if frame_width <= 0 or frame_height <= 0:
        return polygon_pts

    max_x = max(float(p[0]) for p in polygon_pts)
    max_y = max(float(p[1]) for p in polygon_pts)

    if max_x <= 1.0 and max_y <= 1.0:
        return [[float(p[0]) * frame_width, float(p[1]) * frame_height] for p in polygon_pts]

    if frame_width == int(reference_width) and frame_height == int(reference_height):
        return polygon_pts

    scale_x = frame_width / float(reference_width)
    scale_y = frame_height / float(reference_height)
    return [[float(p[0]) * scale_x, float(p[1]) * scale_y] for p in polygon_pts]


def is_point_in_polygon(point: Tuple[float, float], polygon_pts: List[List[float]]) -> bool:
    """
    Check if a 2D point (x, y) is inside or on the boundary of a polygon.
    Uses Shapely if available, otherwise uses Ray-Casting algorithm.
    polygon_pts format: [[x1, y1], [x2, y2], ...]
    """
    if len(polygon_pts) < 3:
        return False

    if SHAPELY_AVAILABLE:
        poly = Polygon(polygon_pts)
        pt = Point(point)
        return poly.contains(pt) or poly.touches(pt)

    # Ray-casting algorithm fallback
    x, y = point
    n = len(polygon_pts)
    inside = False

    p1x, p1y = polygon_pts[0]
    for i in range(n + 1):
        p2x, p2y = polygon_pts[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside
