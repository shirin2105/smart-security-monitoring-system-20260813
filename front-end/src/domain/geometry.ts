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

function doSegmentsIntersect(
  p1: [number, number],
  p2: [number, number],
  p3: [number, number],
  p4: [number, number]
): boolean {
  const ccw = (a: [number, number], b: [number, number], c: [number, number]) =>
    (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0]);

  return (
    ccw(p1, p3, p4) !== ccw(p2, p3, p4) &&
    ccw(p1, p2, p3) !== ccw(p1, p2, p4)
  );
}

export function isTrackInZone(
  bbox: [number, number, number, number],
  frameW: number,
  frameH: number,
  polygon: [number, number][]
): boolean {
  if (!polygon || polygon.length < 3) return false;
  const [bx1, by1, bx2, by2] = bbox;
  const isPercentage = bx1 <= 1 && by1 <= 1 && bx2 <= 1 && by2 <= 1;

  const w = frameW || 1280;
  const h = frameH || 720;

  const x1 = isPercentage ? Math.min(bx1, bx2) : Math.min(bx1, bx2) / w;
  const y1 = isPercentage ? Math.min(by1, by2) : Math.min(by1, by2) / h;
  const x2 = isPercentage ? Math.max(bx1, bx2) : Math.max(bx1, bx2) / w;
  const y2 = isPercentage ? Math.max(by1, by2) : Math.max(by1, by2) / h;

  // Chuẩn hóa toạ độ polygon sang [0, 1] nếu là pixel
  const maxX = Math.max(...polygon.map((p) => p[0]));
  const maxY = Math.max(...polygon.map((p) => p[1]));
  const polyIsNormalized = maxX <= 1.0 && maxY <= 1.0;

  const normPolygon: [number, number][] = polyIsNormalized
    ? polygon
    : polygon.map(([px, py]) => [px / w, py / h]);

  // 1. Kiểm tra các điểm mẫu trọng yếu của đối tượng có nằm trong polygon không
  const samplePoints: [number, number][] = [
    [(x1 + x2) / 2, y2], // Chân người (bottom-center)
    [(x1 + x2) / 2, y1 + (y2 - y1) * 0.75], // Phần thân dưới (75% height)
    [(x1 + x2) / 2, (y1 + y2) / 2], // Tâm đối tượng (center)
    [x1, y2], // Chân trái (bottom-left)
    [x2, y2], // Chân phải (bottom-right)
    [(x1 + x2) / 2, y1], // Đỉnh đầu (top-center)
  ];

  for (const pt of samplePoints) {
    if (isPointInPolygon(pt, normPolygon)) {
      return true;
    }
  }

  // 2. Kiểm tra nếu có bất kỳ đỉnh nào của polygon nằm lọt vào trong bounding box
  for (const [px, py] of normPolygon) {
    if (px >= x1 && px <= x2 && py >= y1 && py <= y2) {
      return true;
    }
  }

  // 3. Kiểm tra các cạnh của bounding box có cắt cạnh nào của polygon không (chạm viền)
  const boxCorners: [number, number][] = [
    [x1, y1],
    [x2, y1],
    [x2, y2],
    [x1, y2],
  ];

  const boxSegments: Array<[[number, number], [number, number]]> = [
    [boxCorners[0], boxCorners[1]], // Top
    [boxCorners[1], boxCorners[2]], // Right
    [boxCorners[2], boxCorners[3]], // Bottom
    [boxCorners[3], boxCorners[0]], // Left
  ];

  const nPoly = normPolygon.length;
  for (let i = 0; i < nPoly; i++) {
    const polyP1 = normPolygon[i];
    const polyP2 = normPolygon[(i + 1) % nPoly];

    for (const [boxP1, boxP2] of boxSegments) {
      if (doSegmentsIntersect(boxP1, boxP2, polyP1, polyP2)) {
        return true;
      }
    }
  }

  return false;
}
