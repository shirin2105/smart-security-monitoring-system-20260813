# Phase 11A — Baseline (frozen Phase 11 state)

Freeze of the Phase 11 (provisional) benchmark before GT hardening. Old
artifacts are NOT overwritten.

## Frozen reference

| Item | Value |
|------|-------|
| Git commit | `02e9f0e` (develop) |
| Benchmark version | `phase11-v1` |
| Runtime profile | BALANCED, inference 5 FPS (1/5 sampling), CUDA RTX 3050 |
| Detector checkpoint | `artifacts/phase7a-results/outputs/.../best.pth` |

## Old (provisional) metrics — Phase 11

| Event | TP | FP | FN | P | R | F1 | FA/h | Median Delay |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ZONE_INTRUSION | 46 | 12 | 14 | 0.79 | 0.77 | 0.78 | 48.7 | 2.24 |
| CROWD_THRESHOLD | 0 | 2 | 18 | 0.0 | 0.0 | 0.0 | 8.1 | - |
| ABANDONED_OBJECT | 0 | 0 | 4 | 0.0 | 0.0 | 0.0 | 0.0 | - |
| Overall (micro) | 46 | 14 | 36 | 0.77 | 0.56 | 0.65 | 56.8 | 2.24 |
| Overall (macro) | - | - | - | 0.26 | 0.26 | 0.26 | - | - |

Duplicate rate 0.118; delay mean 1.88 s, median 2.24 s, P90 2.78 s, max 3.68 s.

## Old artifact paths (frozen, read-only inputs)

- GT: `evaluation/phase11/ground_truth_events.jsonl`
- Manifest: `evaluation/phase11/manifest.json`
- Predictions: `artifacts/phase11/predictions_all.jsonl`
- Error attribution: `artifacts/phase11/error_attribution.csv`
- Report: `artifacts/phase11/benchmark_report.md`

## Runtime config (frozen; MUST NOT change in Phase 11A)

- Crowd: threshold 3, hold 4.0 s, release 2, cooldown 30 s.
- Intrusion: dwell 2.0 s, exit grace 1.0 s, cooldown 30 s.
- Abandoned (Phase7C): stationary hold 3 s, owner-away hold 5 s.
- ROI: central region `[[115,115],[269,115],[269,259],[115,259]]` (384x288).
- Sampling: 1/5 (target 5 FPS from 25 FPS source).

## Phase 11A scope

Validate/harden the GT, trace crowd + abandoned failures, rerun the benchmark
with hardened GT, and only then decide Phase 11B vs Phase 12. **No model / hold
/ sampling / threshold / tracker changes.**
