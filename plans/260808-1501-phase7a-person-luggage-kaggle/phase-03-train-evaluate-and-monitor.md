---
phase: 3
title: "Train, evaluate, and monitor"
status: completed
priority: P1
effort: "30m operator time plus up to 10h runtime"
dependencies: [2]
---

# Phase 3: Train, Evaluate, and Monitor

## Context Links

- Locked training: [guide](C:/Users/trand/Downloads/Others/PHASE7A_AGENT_GUIDE.md:124)
- Full-train entry: [script](C:/Users/trand/Downloads/Others/phase7a_person_luggage_deimv2_kaggle.py:957)
- Evaluation entry: [script](C:/Users/trand/Downloads/Others/phase7a_person_luggage_deimv2_kaggle.py:1302)

## Overview

Monitor the same run through 20-epoch tuning and all six evaluation jobs; intervene only on terminal failures.

## Requirements and Data Flow

Smoke-approved manifests + Phase-4 `best.pth` → DEIMv2-S 640, 20 epochs, global batch 16 on T4x2 (8 fallback on one T4), AMP/EMA, locked LR/WD/warmup/drop/augmentations, `-t` → `last.pth` and best alias → same best model → combined, VisDrone-person, COCO-luggage validation × full640/tile768-overlap20 → predictions and summary. Evaluation must use validation sets only.

## Related Files and Ownership

- No repository file edits. Runtime version and its outputs are immutable evidence.

## Implementation Steps

1. Monitor epoch progress, losses, validation metrics, checkpoint writes, GPU utilization/VRAM, OOM/NCCL errors, and unmatched score-head warning.
2. Treat 10→4 score-head unmatched keys during `-t` as expected; do not strict-patch loader ([guide](C:/Users/trand/Downloads/Others/PHASE7A_AGENT_GUIDE.md:146)).
3. Verify `best.pth` exists before evaluation and that all six jobs complete with nonempty prediction files.
4. Capture overall AP50:95/AP50/AP75/AP-small/AR-small plus FPS, tiles/image, VRAM; capture per-class AP/AP50/AR100 for each applicable class.

## Test Matrix and Success Criteria

| Level | Check | Pass condition |
|---|---|---|
| Runtime | training | 20 epochs terminate; `last.pth` and `best.pth` exist |
| Integration | checkpoint load | strict evaluation load succeeds on chosen best |
| E2E | evaluation | 3 datasets × 2 modes = 6 complete result records |
| Contract | metrics | overall + per-class + throughput/VRAM fields present and finite where class exists |

- [x] `PHASE 7A FINAL EVALUATION` captured.
- [x] Required per-class tile-mode sections captured for VisDrone-person and COCO-luggage.

## Risk Assessment and Rollback

- Medium × high: OOM/NCCL/runtime timeout. Mitigate inspect traceback and allow runtime-only worker/environment compatibility fix; one-T4 batch-8 fallback is already scripted, but record deviation.
- Medium × high: best alias falls back to last when `best_stg1.pth` missing. Record warning explicitly; do not misreport selection.
- Rollback: preserve last complete Kaggle version; retry from Phase 2 smoke with `-t`, never resume via `-r` or splice partial metrics.

## Next Steps

Only a successful terminal version with six evaluations advances.

## Unresolved Questions

None.
