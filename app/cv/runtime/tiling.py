"""Adaptive tiling: full-frame (full640) vs tiled (tile768_overlap20).

``AdaptiveTiling`` decides which inference mode to use with hysteresis/minimum
hold time so the mode does not switch on every frame. ``plan_tiles`` and
``merge_detections`` implement the actual tiling pipeline for high-res scenes.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from app.common.schemas import DetectionResult
from app.cv.runtime.config import AdaptiveTilingConfig, RuntimePerformanceConfig
from app.cv.runtime.profiles import FULL_FRAME_MODE, TILE_MODE, is_high_resolution


def _default_clock() -> float:
    return time.monotonic()


@dataclass(frozen=True)
class TileRegion:
    """A crop region (x1, y1, x2, y2) plus its pixel buffer."""

    x1: int
    y1: int
    x2: int
    y2: int
    image: Any

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1


def plan_tiles(
    frame: Any,
    tile_size: int = 768,
    overlap_ratio: float = 0.20,
    min_area: int = 0,
) -> list[TileRegion]:
    """Split a frame into overlapping tiles.

    Returns an empty list when the frame is small enough to run full-frame.
    Tiles overlap by ``overlap_ratio`` so objects crossing a seam are detected
    in at least one tile and merged later.
    """
    image = np.asarray(frame)
    if image.ndim != 3:
        raise ValueError("plan_tiles requires an HxWx3 image")
    height, width = image.shape[:2]
    if height <= tile_size and width <= tile_size:
        return []
    if width * height < min_area:
        return []
    step = max(1, int(tile_size * (1.0 - overlap_ratio)))
    tiles: list[TileRegion] = []
    y = 0
    while y < height:
        x = 0
        while x < width:
            x1, y1 = x, y
            x2, y2 = min(width, x + tile_size), min(height, y + tile_size)
            tiles.append(TileRegion(x1, y1, x2, y2, image[y1:y2, x1:x2].copy()))
            if x2 >= width:
                break
            x = max(x2 - step, x + 1)
        if y2 >= height:
            break
        y = max(y2 - step, y + 1)
    return tiles


def _iou(box_a: list[float], box_b: list[float]) -> float:
    x1 = max(box_a[0], box_b[0])
    y1 = max(box_a[1], box_b[1])
    x2 = min(box_a[2], box_b[2])
    y2 = min(box_a[3], box_b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_a = max(0.0, box_a[2] - box_a[0]) * max(0.0, box_a[3] - box_a[1])
    area_b = max(0.0, box_b[2] - box_b[0]) * max(0.0, box_b[3] - box_b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def merge_detections(detections: list[DetectionResult], iou_threshold: float = 0.5) -> list[DetectionResult]:
    """NMS-merge per-tile detections (already offset to full-frame coordinates)."""
    if len(detections) <= 1:
        return list(detections)
    ordered = sorted(detections, key=lambda item: item.confidence, reverse=True)
    kept: list[DetectionResult] = []
    for candidate in ordered:
        duplicate = False
        for existing in kept:
            if candidate.class_id != existing.class_id:
                continue
            if _iou(candidate.bbox, existing.bbox) >= iou_threshold:
                duplicate = True
                break
        if not duplicate:
            kept.append(candidate)
    return kept


def _offset_detections(tile: TileRegion, detections: list[DetectionResult]) -> list[DetectionResult]:
    return [
        DetectionResult(
            class_id=d.class_id,
            class_name=d.class_name,
            bbox=[d.bbox[0] + tile.x1, d.bbox[1] + tile.y1, d.bbox[2] + tile.x1, d.bbox[3] + tile.y1],
            confidence=d.confidence,
        )
        for d in detections
    ]


class AdaptiveTiling:
    """Decides full640 vs tile768_overlap20 with minimum-mode-hold hysteresis."""

    def __init__(
        self,
        config: RuntimePerformanceConfig,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._config = config
        self._clock = clock or _default_clock
        self._mode = FULL_FRAME_MODE
        self._mode_since = float("-inf")
        self._decisions = 0

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def decisions(self) -> int:
        return self._decisions

    def select(self, source_area_px: float, load_allows_tiling: bool, profile_tiling: str) -> str:
        """Choose the inference mode for the current scene.

        ``profile_tiling`` is the profile's tiling intent (full640, adaptive,
        tile768_overlap20). Hysteresis prevents flapping within the minimum hold
        window.
        """
        self._decisions += 1
        if not self._config.adaptive.enabled:
            self._set_mode(FULL_FRAME_MODE)
            return self._mode
        if profile_tiling == FULL_FRAME_MODE:
            self._set_mode(FULL_FRAME_MODE)
            return self._mode
        if profile_tiling == TILE_MODE:
            self._set_mode(TILE_MODE)
            return self._mode

        # ADAPTIVE intent: tile only for high-res scenes when load allows it.
        desired = (
            TILE_MODE
            if is_high_resolution(source_area_px, self._config) and load_allows_tiling
            else FULL_FRAME_MODE
        )
        now = self._clock()
        if desired == self._mode:
            return self._mode
        if (now - self._mode_since) < self._config.adaptive.min_mode_hold_s:
            return self._mode
        self._set_mode(desired)
        return self._mode

    def _set_mode(self, mode: str) -> None:
        if mode != self._mode:
            self._mode = mode
            self._mode_since = self._clock()

    def reset(self) -> None:
        self._mode = FULL_FRAME_MODE
        self._mode_since = self._clock()


def infer_tiles(
    detector: Any,
    frame_data: Any,
    tile_size: int,
    overlap_ratio: float,
    nms_iou_threshold: float,
) -> tuple[list[DetectionResult], float]:
    """Run detector per tile, offset and NMS-merge, returning full-frame detections.

    ``detector`` must accept a ``FrameData`` (the DEIMv2 contract). Each tile is
    handed to the detector as a shallow copy of the frame with the tile crop in
    ``.image`` so coordinates stay tile-local and are then offset to full-frame.
    """
    image = getattr(frame_data, "image", None)
    if image is None:
        return detector.detect(frame_data)
    tiles = plan_tiles(image, tile_size=tile_size, overlap_ratio=overlap_ratio)
    if not tiles:
        return detector.detect(frame_data)
    merged: list[DetectionResult] = []
    total_latency = 0.0
    for tile in tiles:
        tile_frame = frame_data.model_copy(update={"image": tile.image})
        detections, latency = detector.detect(tile_frame)
        total_latency += latency
        merged.extend(_offset_detections(tile, detections))
    return merge_detections(merged, iou_threshold=nms_iou_threshold), total_latency
