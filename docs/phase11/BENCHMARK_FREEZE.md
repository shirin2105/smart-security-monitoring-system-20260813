# Phase 11 — Benchmark Freeze

This file freezes the exact runtime/config/data used for the Phase 11 final CV
benchmark. **No configuration is changed per clip during the run.**

## Freeze record

| Item | Value |
|------|-------|
| Git commit | `02e9f0e` (develop, `docs(cv): close phase 9.1 validation`) |
| Benchmark version | `phase11-v1` |
| Date | 2026-08-15 |
| Runtime path | RTSP/Video → scheduler/adaptive inference → DEIMv2 → ByteTrack → shared TrackStore → Intrusion/Crowd/Phase7C → CVEventManager → cv-event-v1 |

## Detector

| Item | Value |
|------|-------|
| Model | DEIMv2-S (person/luggage) |
| Checkpoint | `artifacts/phase7a-results/outputs/phase7a_deimv2_s_person_luggage/best.pth` |
| Backbone | `third_party/deimv2/ckpts/vitt_distill.pt` |
| Confidence threshold | 0.05 |
| NMS IoU | 0.50 |
| Device | CUDA (NVIDIA GeForce RTX 3050 Laptop GPU) |

## Runtime

| Item | Value |
|------|-------|
| Runtime profile | BALANCED (Phase 10B default) |
| Inference FPS (target) | 5 (frame sampling) |
| Adaptive tiling | enabled, threshold 1.5M px, tile768_overlap20 |
| Scheduler | round_robin, starvation 1500 ms |
| Tracker | ByteTrack (lost buffer 30, activation 0.25, min consecutive 2) |
| Latency budget | preferred 500 / acceptable 1000 / overloaded 1500 ms |

## Event thresholds (benchmark camera config, frozen)

- Intrusion: dwell 2.0 s, exit grace 1.0 s, cooldown 30 s; ROI = central region of each clip.
- Crowd: count_threshold 3, hold 4 s, release 2, cooldown 30 s.
- Abandoned (Phase7C): stationary hold 3 s, owner-away hold 5 s; valid floor ROI = central region.

## Evaluation

| Item | Value |
|------|-------|
| Evaluator | `app/evaluation/phase11_evaluator.py` |
| Matching | clip + camera + event_type + temporal window |
| Tolerance | ZONE_INTRUSION ±2 s, CROWD_THRESHOLD ±3 s, ABANDONED_OBJECT ±5 s |
| Matching window | `[trigger_time_s - tolerance, end_s + tolerance]` (early gate = tolerance; late bound = event end + tolerance, late alerts flagged LATE_ALERT) |
| Matching rule | one-to-one (a prediction cannot match two GT) |
| Metrics | TP/FP/FN, Precision/Recall/F1 (micro + macro), FA/h, delay (mean/median/P90/max), duplicate rate |
| Lifecycle collapse | START/UPDATE/END → one event instance (UPDATE not counted) |

## Dataset

- Source: `phase8_dataset/videos/*.mpg` (CAVIAR scenario clips).
- Ground truth: derived deterministically from `phase8_dataset/source_xml/*.xml`
  (CAVIAR per-frame trajectory labels) via `app/evaluation/phase11_gt_extractor.py`.
- GT is **provisional/heuristic** (see Limitations in the report) because
  frame-level event annotation was not visually verified.

## Protocol

1. Freeze (this file). 2. validate manifest. 3. validate GT. 4. synthetic
evaluator dry-run (tests). 5. infer all clips. 6. merge predictions.
7. evaluate. 8. inspect FP/FN. 9. attribute errors. 10. report.
11. decide Phase11B vs Phase12. No tuning between steps 5 and 7.
