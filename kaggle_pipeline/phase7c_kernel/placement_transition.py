"""Behavior-neutral placement-transition features from synchronized tracks."""

from __future__ import annotations

from typing import Sequence

import numpy as np


MAX_GAP_S = 0.5
MIN_SAMPLES = 4
MIN_INTERVALS = 3
MIN_DURATION_S = 0.6
MIN_BAG_MOTION_NORM = 0.25
MIN_ALIGNED_RATIO = 0.60
MIN_MEDIAN_COSINE = 0.50
MAX_OFFSET_SPREAD_NORM = 0.35
MIN_MOVING_STEP_NORM = 0.02


def _insufficient(sample_count: int = 0, duration_s: float = 0.0) -> dict:
    return {
        "schema": "placement-transition-features-v1",
        "evidence_sufficient": False,
        "placement_predicate_passed": False,
        "sample_count": sample_count,
        "interval_count": max(0, sample_count - 1),
        "duration_s": duration_s,
        "bag_motion_norm": None,
        "aligned_moving_ratio": None,
        "median_direction_cosine": None,
        "relative_offset_spread_norm": None,
    }


def placement_transition_features(observations: Sequence[dict]) -> dict:
    """Summarize the final valid contiguous synchronized segment, fail closed."""
    if not observations:
        return _insufficient()
    ordered = sorted(observations, key=lambda item: float(item["timestamp_s"]))
    times = np.asarray([item["timestamp_s"] for item in ordered], dtype=np.float64)
    if not np.all(np.isfinite(times)) or len(np.unique(times)) != len(times):
        return _insufficient(len(ordered))
    gaps = np.diff(times)
    split = np.where(gaps > MAX_GAP_S)[0]
    if len(split):
        ordered = ordered[int(split[-1]) + 1:]
        times = times[int(split[-1]) + 1:]
    duration = float(times[-1] - times[0]) if len(times) > 1 else 0.0
    if len(ordered) < MIN_SAMPLES or len(ordered) - 1 < MIN_INTERVALS or duration < MIN_DURATION_S:
        return _insufficient(len(ordered), duration)

    bag = np.asarray([item["bag_center"] for item in ordered], dtype=np.float64)
    person = np.asarray([item["person_center"] for item in ordered], dtype=np.float64)
    boxes = np.asarray([item["person_bbox"] for item in ordered], dtype=np.float64)
    if not all(np.all(np.isfinite(value)) for value in (bag, person, boxes)):
        return _insufficient(len(ordered), duration)
    diagonals = np.hypot(boxes[:, 2] - boxes[:, 0], boxes[:, 3] - boxes[:, 1])
    scale = float(np.median(diagonals))
    if not np.isfinite(scale) or scale <= 0:
        return _insufficient(len(ordered), duration)

    bag_steps = np.diff(bag, axis=0) / scale
    person_steps = np.diff(person, axis=0) / scale
    bag_lengths = np.linalg.norm(bag_steps, axis=1)
    person_lengths = np.linalg.norm(person_steps, axis=1)
    moving = (bag_lengths >= MIN_MOVING_STEP_NORM) & (person_lengths >= MIN_MOVING_STEP_NORM)
    cosines = np.full(len(bag_steps), -1.0, dtype=np.float64)
    cosines[moving] = np.sum(bag_steps[moving] * person_steps[moving], axis=1) / (
        bag_lengths[moving] * person_lengths[moving]
    )
    aligned = moving & (cosines >= MIN_MEDIAN_COSINE)
    aligned_ratio = float(np.mean(aligned))
    median_cosine = float(np.median(cosines[moving])) if np.any(moving) else -1.0
    offsets = (bag - person) / scale
    center = np.median(offsets, axis=0)
    offset_spread = float(np.percentile(np.linalg.norm(offsets - center, axis=1), 90))
    bag_motion = float(np.sum(bag_lengths))
    passed = bool(
        bag_motion >= MIN_BAG_MOTION_NORM
        and aligned_ratio >= MIN_ALIGNED_RATIO
        and median_cosine >= MIN_MEDIAN_COSINE
        and offset_spread <= MAX_OFFSET_SPREAD_NORM
    )
    return {
        "schema": "placement-transition-features-v1",
        "evidence_sufficient": True,
        "placement_predicate_passed": passed,
        "sample_count": len(ordered),
        "interval_count": len(ordered) - 1,
        "duration_s": duration,
        "bag_motion_norm": bag_motion,
        "aligned_moving_ratio": aligned_ratio,
        "median_direction_cosine": median_cosine,
        "relative_offset_spread_norm": offset_spread,
    }
