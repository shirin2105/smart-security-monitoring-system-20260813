---
title: "DEIMv2 Phase 5B Kaggle tiled inference sweep"
description: "Run the supplied inference-only sweep in a separate one-T4 Kaggle kernel and retain auditable results and failure evidence."
status: pending
priority: P1
effort: 1.5h operator time plus Kaggle runtime
branch: model-CV-v1
tags: [deimv2, kaggle, visdrone, inference, evaluation]
created: 2026-08-07
---

# DEIMv2 Phase 5B Kaggle Tiled Inference Sweep

## Outcome

Submit the user-supplied Phase 5B source byte-for-byte to a new private Kaggle script using the existing VisDrone and Phase 4 best-checkpoint datasets, monitor it to a terminal state, download its artifacts, and report the exact final comparison table and `BEST` lines. No training or model/data changes.

## Scope

- In: local static validation, isolated kernel package, Kaggle push/status monitoring, output/log retrieval, evidence extraction.
- Out: retraining, architecture, S4, EdgeCrafter, YOLO, VLM, dataset/checkpoint mutation, GitHub commit/push.
- Source changes prohibited unless a reproduced runtime blocker is diagnosed, explained, and separately approved.

## Verified Basis

- Existing Phase 5 used 548 validation images, one T4, and the same checkpoint ([report](../../reports/deimv2_phase5_tiling_report.md#scope)).
- Existing Kaggle inputs are `duwipurnamasidik/visdrone-2019-coco-format` and `shirin21st/deimv2-s-visdrone-phase4-best` ([metadata](../../kaggle_pipeline/phase5_kernel/kernel-metadata.json)).
- Phase 5B defines eight experiments and emits JSON, CSV, Markdown, predictions, final table, and two `BEST` outcomes (`C:/Users/trand/Downloads/Others/deimv2_phase5b_tiling_sweep.py:44`, `:51`, `:998`, `:1079`).

## Phases

| Phase | Status | Deliverable | Depends on |
|---|---|---|---|
| [1](phase-01-package-and-validate.md) | pending | Byte-identical isolated kernel package passes static gates | none |
| [2](phase-02-submit-and-monitor.md) | pending | New one-T4 Kaggle version reaches COMPLETE or yields full failure evidence | 1 |
| [3](phase-03-retrieve-and-report.md) | pending | Downloaded outputs, exact table/BEST lines, integrity checks | 2 COMPLETE |

## Dependency and Ownership

Sequential only. Phase 1 owns the new local kernel directory. Phase 2 owns Kaggle version submission/status only. Phase 3 owns a new local artifact-download directory and final run report. No phase modifies the supplied source, existing Phase 5 kernel, datasets, checkpoint, or project docs.

## End-to-End Data Flow

Supplied Python bytes + new metadata -> local static gates -> Kaggle private kernel -> attached immutable VisDrone/checkpoint inputs -> normalized validation annotations -> eight inference/evaluation results -> `/kaggle/working/phase5b_deimv2_tiling_sweep/` -> local artifact bundle + captured kernel log -> exact evidence report.

## Success Criteria

- One new private Kaggle kernel uses one `NvidiaTeslaT4`, internet enabled, and exactly the two verified dataset sources.
- Source SHA-256 before packaging equals packaged/submitted source SHA-256.
- Terminal status reaches COMPLETE; all eight unique experiment rows exist in JSON/CSV/Markdown.
- Baseline sanity result is recorded; if outside tolerance, tiling deltas are explicitly non-interpretable.
- Exact final comparison table and both emitted `BEST` lines are retained verbatim from the kernel log and cross-checked against JSON.
- No GitHub commit/push and no out-of-scope code/data change.

## Rollback

Local rollback: remove only the newly created kernel package/download directories. Remote rollback: leave the failed/superseded private version as evidence or delete only the new kernel after output capture and explicit approval. Existing Phase 5 kernel and datasets remain untouched.

## Validation Log

- Tier: Standard; claims checked: 10; verified: 10; failed: 0; unverified: 0.
- Whole-plan consistency: 4 files reread after creation; stale decisions: 0; unresolved contradictions: 0.

## Unresolved Questions

None.
