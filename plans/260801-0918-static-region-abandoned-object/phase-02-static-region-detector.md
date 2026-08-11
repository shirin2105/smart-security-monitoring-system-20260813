---
phase: 2
title: "Static-region detector"
status: completed
priority: P1
effort: 4h
dependencies: [1]
---

# Phase 02: Static-region detector

## Context Links

- `app/cv/detector.py:13-69` is class-based YOLO inference.
- `app/cv/frame_sampler.py:4-14` controls processed-frame cadence.
- `configs/event_rules.yaml:12-21` holds abandoned-object thresholds.

## Overview

Add one camera-scoped OpenCV background/static-region component. It detects persistent introduced foreground, independent of object class.

## Requirements

- Functional: warm background, clean mask, reject tiny/huge regions, associate contours across frames by IoU/centroid, mature after elapsed media time, clear after absence.
- Non-functional: fixed-camera assumption explicit; bounded state/history; deterministic given identical frames/timestamps/config; component under 200 lines where practical.

## Architecture and data flow

Raw BGR frame -> grayscale/blur -> OpenCV background subtractor -> threshold + open/close morphology -> contours -> area/aspect filters -> region association -> per-camera pending/static/cleared state -> `StaticRegionObservation[]`. During warm-up, update baseline but emit none. Freeze/slow background learning under matched persistent regions to avoid absorbing the candidate.

## Related Code Files / Ownership

- Create: `app/cv/static_region_detector.py`, `tests/unit/test_static_region_detector.py`
- Modify: `configs/event_rules.yaml`
- Delete: none

## Implementation Steps

1. Write synthetic-frame tests: baseline warm-up, introduced rectangle maturity, transient rejection, jitter association, disappearance clearing, person-sized moving blob rejection by persistence.
2. Implement camera-local detector with explicit `reset()`; use elapsed `captured_at`, never processed frame count, for maturity.
3. Add conservative config: warm-up seconds, min/max area ratio, morphology kernel, match threshold, stationary seconds, clear grace, learning rate.
4. Bound unmatched region retention and validate malformed/empty frames as no observation plus safe reset/error signal.

## Todo List

- [x] Add test fixture generator using NumPy frames.
- [x] Implement warm-up/mask/contour pipeline.
- [x] Implement association, maturity, and cleanup.
- [x] Run `pytest tests/unit/test_static_region_detector.py`.

## Success Criteria

- [x] Unclassified introduced region matures at configured media time ± one sampled frame.
- [x] Baseline and short-lived regions emit zero mature observations.
- [x] State remains bounded after 10,000 synthetic frames.

## Risk Assessment

- High likelihood/high impact: illumination/shadow creates large foreground. Mitigation: area caps, morphology, persistence, warm-up, shadow threshold, real-clip calibration.
- High likelihood/high impact: background model absorbs stationary object. Mitigation: controlled learning mask/rate and regression test.
- Medium likelihood/high impact: camera shake violates assumption. Mitigation: reject global-motion masks and document unsupported moving cameras.

## Security Considerations

Frames remain in process. No persistence added here.

## Rollback

Remove the new component/config keys; no existing runtime path calls it before phase 03.

## Next Steps

Phase 03 adapts mature regions to the current event contract and worker.
