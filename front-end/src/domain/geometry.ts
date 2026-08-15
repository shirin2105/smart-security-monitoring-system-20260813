/**
 * Geometry helpers for frontend bounding box and zone calculations.
 */

export function isPointInPolygon(point: [number, number], polygon: [number, number][]): boolean {
  if (!polygon || polygon.length < 3) return false;
  const [x, y] = point;
  let inside = false;
  const n = polygon.length;
  let j = n - 1;
  for (let i = 0; i < n; i++) {
    const [xi, yi] = polygon[i];
    const [xj, yj] = polygon[j];
    const crosses = (yi > y) !== (yj > y);
    if (crosses) {
      const xIntersect = ((xj - xi) * (y - yi)) / ((yj - yi) || 1e-12) + xi;
      if (x < xIntersect) {
        inside = !inside;
      }
    }
    j = i;
  }
  return inside;
}

export function isTrackInZone(
  bbox: [number, number, number, number],
  frameW: number,
  frameH: number,
  polygon: [number, number][]
): boolean {
  if (!polygon || polygon.length < 3) return false;
  const [x1, y1, x2, y2] = bbox;
  const isPercentage = x1 <= 1 && y1 <= 1 && x2 <= 1 && y2 <= 1;

  // Điểm chân người (foot point)
  const normFootX = isPercentage ? (x1 + x2) / 2 : (x1 + x2) / (2 * (frameW || 1280));
  const normFootY = isPercentage ? y2 : y2 / (frameH || 720);

  // Chuẩn hóa toạ độ polygon sang [0, 1] nếu là pixel
  const maxX = Math.max(...polygon.map((p) => p[0]));
  const maxY = Math.max(...polygon.map((p) => p[1]));
  const polyIsNormalized = maxX <= 1.0 && maxY <= 1.0;

  const normPolygon: [number, number][] = polyIsNormalized
    ? polygon
    : polygon.map(([px, py]) => [px / (frameW || 1280), py / (frameH || 720)]);

  return isPointInPolygon([normFootX, normFootY], normPolygon);
}
