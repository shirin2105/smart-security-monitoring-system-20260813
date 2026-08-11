---
title: Phase 8 CV E2E validation
status: in-progress
priority: P0
effort: high
branch: model-CV-v1
tags: [computer-vision, event-evaluation, kaggle]
created: 2026-08-10
---

# Phase 8 — CV E2E validation

## Outcome

Validate `ZONE_INTRUSION`, `CROWD_THRESHOLD`, and `ABANDONED_OBJECT` on 20–30 real
positive/negative clips. Report P/R/F1, false alarms/hour, delay, and FP/FN cause.

## Frozen scope

- DEIMv2-S Phase 7A checkpoint; no retraining.
- Class-wise ByteTrack and current Phase 7C abandoned-object reasoning.
- `full640` default; `tile768_overlap20` only by camera configuration.
- Computer Vision only. No S4, EdgeCrafter, YOLO, VLM, backend, or dashboard.
- No component change before evidence-based error attribution.

## Progress — 8/10 tasks (80%)

- [x] Freeze runtime/model/tracker/event contracts.
- [x] Define one JSONL prediction schema for all three event types.
- [x] Implement thin `inference_video.py` adapter over existing CV components.
- [x] Implement fail-closed batch runner and Kaggle launcher package.
- [x] Implement event matching, precision/recall/F1, false-rate, and delay evaluator.
- [x] Implement manifest/camera-config validation and attribution worksheet tooling.
- [x] Verify 19 focused contract tests and local ABODA smoke run.
- [x] Identify and label one 20–30 clip positive/negative validation dataset.
- [ ] Attach that dataset, run Kaggle batch, and retrieve complete outputs.
- [ ] Review every FP/FN attribution; publish final metrics and next bottleneck.

## Evidence

- Focused test suite: `19 passed`, `0 failed`, 2026-08-10.
- CAVIAR dataset gate: 20 original videos, 20 XML files, 20 camera configs,
  886.72 seconds, 45 GT events; focused suite now 26/26.
- Kaggle Dataset: `shirin21st/phase8-caviar-cv-validation`, version 2 verified
  with all 20 videos. Kernel v1 exposed a missing support-file packaging defect;
  private code Dataset attached. Kernel v2 exposed a BOM-bearing manifest; the
  compatible loader was published in code Dataset v2 and kernel v3 observed running.
  Kernel v3 then exposed an omitted Phase 7C core after the first tracker run;
  code Dataset v3 includes an import-tested core and kernel v4 was observed running.
- Local smoke: 5,019 track rows; 11 schema-valid predictions.
- Tooling status: adapter, schema, evaluator, config validator, batch runner,
  Kaggle launcher, examples, tests, and operational README implemented.
- Metric status: not available; two-clip smoke is not the required validation set.

## Gate status

| Gate | Status | Evidence / missing item |
|---|---|---|
| Three engines run batch E2E | running | 20-clip CAVIAR batch submitted to Kaggle |
| Unified prediction schema | complete | adapter and schema tests pass |
| TP/FP/FN + false alarms/hour + delay | tooling complete | needs real GT/predictions |
| Every FP/FN attributed | blocked | needs batch output and human video review |
| Bottleneck identified | blocked | depends on reviewed attribution |

Overall Phase 8 remains **in progress**. Tooling completion is not validation completion.

## Blockers, risks, and unblock paths

| Item | Owner | Impact | Unblock / close condition |
|---|---|---|---|
| Kaggle outputs absent | CV owner after data attach | no production metrics | batch completes for every manifest clip; outputs downloaded |
| FP/FN attribution unreviewed | CV reviewer | no safe tuning decision | inspect every unmatched event; replace `UNKNOWN` with evidence-backed cause |
| Small smoke may hide runtime faults | CV owner | E2E confidence limited | close after full fail-closed batch passes |

No scope change. External validation data is a planned dependency, now the critical
path. Finishing the remaining three tasks is required before Phase 8
can be declared complete or Phase 8B/Phase 9 can be selected.

## Next actions

1. CV owner: retrieve the running frozen Kaggle batch; done when every clip has prediction JSONL and measured processed duration.
2. CV reviewer: complete attribution and report; done when no FP/FN remains unreviewed and the bottleneck is evidence-backed.

## Unresolved questions

- Which component dominates errors after the reviewed CAVIAR benchmark?
