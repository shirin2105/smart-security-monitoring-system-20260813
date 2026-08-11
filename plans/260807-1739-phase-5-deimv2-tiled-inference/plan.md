---
title: "Phase 5 DEIMv2 tiled inference"
description: "Run a controlled Kaggle ablation of full-frame and tiled DEIMv2-S inference on VisDrone validation data."
status: completed
priority: P1
effort: 8h
branch: model-CV-v1
tags: [computer-vision, deimv2, visdrone, kaggle, evaluation]
created: 2026-08-07
---

# Phase 5 DEIMv2 tiled inference

## Outcome

A separate private Kaggle script evaluates one persisted Phase-4 checkpoint on the same 548-image VisDrone validation set using `baseline_640`, `tile640_no_overlap`, and `tile640_overlap25`, then publishes reproducible COCO accuracy, timing, VRAM, provenance, and baseline deltas. No training code or successful Phase-4 kernel is changed.

## Scope

- In: checkpoint Kaggle Dataset, pinned DEIMv2 checkout, normalized validation working copy, three inference modes, COCO metrics, timing, output validation, Kaggle push/run/download workflow.
- Out: retraining, train images, S4, ECDet/EdgeCrafter benchmarking, YOLO, VLM, detector/checkpoint changes, edits to the Phase-4 kernel.

## Data flow

`Kaggle Dataset(best.pth + optional vitt_distill.pt)` + `VisDrone val JSON/images` -> input/provenance gates -> raw IDs `1..10 => 0..9`, drop `0/11` into a working JSON -> one strict DEIMv2-S model -> full frame or native 640 tiles -> postprocess -> tile offset/clip/class-aware NMS (tiles only) -> original-image COCO predictions -> COCOeval + synchronized timing -> JSON/CSV/Markdown summaries -> downloaded run artifacts.

## Dependency graph

1. Persist/attach checkpoint Dataset and record immutable Dataset version.
2. Create separate Phase-5 kernel files; blocked by step 1 metadata.
3. Local static/unit checks; blocked by step 2.
4. Kaggle push and baseline gate; blocked by steps 1-3.
5. Tiled runs, artifact audit, decision; blocked by baseline reproduction within `0.015` of `0.2271`.

No overlap with existing application plans: this plan owns only a new Kaggle artifact directory and external Kaggle Dataset/kernel resources.

## Phase

- [Phase 01 — Build, validate, and run isolated evaluator](phase-01-build-validate-run-isolated-evaluator.md) — completed (8/8 todos)

## Files and ownership

- Create only: `artifacts/kaggle-phase5-deimv2-tiling/deimv2-phase5-tiling-eval.py`, `artifacts/kaggle-phase5-deimv2-tiling/kernel-metadata.json`.
- Read-only references: `artifacts/kaggle-latest-kernel/deimv2-visdrone-train.py`, `artifacts/kaggle-latest-kernel/kernel-metadata.json`, external reference script and contract.
- External artifacts: versioned checkpoint Kaggle Dataset; separate Phase-5 Kaggle kernel; downloaded `phase5_deimv2_tiling/` outputs.

## Measurable success

- Same checkpoint hash, validation image IDs/count, commit, config, preprocessing, score threshold, and GPU recorded for all modes.
- Baseline AP50:95 is within `±0.015` of `0.2271`; otherwise tiled interpretation is blocked.
- All three prediction JSON files and complete JSON/CSV/Markdown summaries pass schema/count/finite-value checks.
- Decision cites AP-small, AR-small, latency/FPS, then overall AP; no visual-only success claim.

## Delivery status

- Progress: 8/8 todos (100%). Kaggle kernel reached `COMPLETE`; all three prediction files and summaries downloaded.
- Checkpoint blocker resolved: private Dataset `shirin21st/deimv2-s-visdrone-phase4-best`; local `best.pth` is 156,501,182 bytes, SHA-256 `DBE9665CD9DACB530629229545C9BED6FF50C2B7E5244EC90065915D184294CC`.
- Kernel blocker resolved: separate kernel `shirin21st/deimv2-phase-5-tiling-evaluation` ran on one Tesla T4.
- Results verified in `artifacts/phase5-results/phase5_deimv2_tiling/` and `reports/deimv2_phase5_tiling_report.md`.
- Quality gate evidence: `plans/reports/tester-260807-phase5-results.md` records compilation, source-integrity, summary consistency, and full prediction-schema validation.

## Unresolved questions

- Whether the approximately fourfold latency increase is acceptable on target deployment hardware.
