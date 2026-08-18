from typing import List, Tuple

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
