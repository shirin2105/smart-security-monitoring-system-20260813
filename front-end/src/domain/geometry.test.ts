import { describe, expect, it } from 'vitest';
import { isPointInPolygon, isTrackInZone } from './geometry';

describe('geometry helper', () => {
  it('isPointInPolygon detects inside and outside correctly', () => {
    const polygon: [number, number][] = [
      [0, 0],
      [100, 0],
      [100, 100],
      [0, 100],
    ];

    expect(isPointInPolygon([50, 50], polygon)).toBe(true);
    expect(isPointInPolygon([150, 50], polygon)).toBe(false);
    expect(isPointInPolygon([50, 150], polygon)).toBe(false);
  });

  it('isTrackInZone detects track foot point in pixel polygon', () => {
    const polygon: [number, number][] = [
      [100, 100],
      [500, 100],
      [500, 500],
      [100, 500],
    ];
    // Track bbox [x1, y1, x2, y2] -> foot point ((x1+x2)/2, y2)
    // In frame 1280x720: [200, 200, 400, 400] -> foot point (300, 400), which is inside polygon
    expect(isTrackInZone([200, 200, 400, 400], 1280, 720, polygon)).toBe(true);

    // Foot point (800, 600) -> outside polygon
    expect(isTrackInZone([700, 500, 900, 600], 1280, 720, polygon)).toBe(false);
  });

  it('isTrackInZone detects track foot point with percentage bbox and pixel polygon', () => {
    const polygon: [number, number][] = [
      [0, 0],
      [640, 0],
      [640, 720],
      [0, 720],
    ];
    // Left half of 1280x720 frame
    // Percentage bbox [0.1, 0.1, 0.3, 0.5] -> norm foot (0.2, 0.5) -> (256, 360) in 1280x720 -> inside
    expect(isTrackInZone([0.1, 0.1, 0.3, 0.5], 1280, 720, polygon)).toBe(true);

    // Right half bbox [0.7, 0.1, 0.9, 0.5] -> norm foot (0.8, 0.5) -> (1024, 360) -> outside
    expect(isTrackInZone([0.7, 0.1, 0.9, 0.5], 1280, 720, polygon)).toBe(false);
  });
});
