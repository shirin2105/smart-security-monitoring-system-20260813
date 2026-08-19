# Placement-Transition Separation Report

## Run

- Real CUDA: NVIDIA GeForce RTX 3050 Laptop GPU
- Runtime: unchanged DEIMv2 + ByteTrack + production Phase7C
- Clips: `cut.mp4`, `pets2006_3.mp4`, `store-aisle-detection.mp4` from `tests/clips`
- Artifact root: `artifacts/placement-transition/diagnostic-three-clips`
- Event equivalence: all three remained at zero abandoned START

## Frozen-predicate result

| Clip | Role | Sufficient rows | Predicate passes | Best observed bag motion norm |
|---|---|---:|---:|---:|
| cut | positive | 40 | 0 | 0.0261 |
| pets2006_3 | positive | 22 | 0 | 0.0392 |
| store-aisle-detection | negative | 508 | 0 | 0.0087 |

The frozen predicate requires normalized pre-placement bag motion >=0.25 plus aligned co-motion. Both positives fail because the detector/tracker history used by owner association begins when the detected luggage is already nearly stationary. The required moving-with-owner segment is absent from the observable luggage track, so placement transition cannot be proven from current synchronized histories.

## Decision

`PLACEMENT_TRANSITION_NOT_PROVEN`

Phase 3 is not authorized. Production owner selection, score, ranking, threshold, stationary, and lifecycle behavior remain unchanged. Do not tune the predicate against these outcomes without a new calibration/holdout design.

The full nine-clip production baseline completed separately, but placement sidecars were generated only for the two owner-stage positives and the hardest owner-stage negative. Because both required positives failed the frozen predicate, the proof gate failed early; this is not a claim of manifest-wide placement separation.
