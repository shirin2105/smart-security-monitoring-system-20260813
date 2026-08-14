---
phase: 1
title: "Build, validate, and run isolated evaluator"
status: completed
priority: P1
effort: 8h
dependencies: []
---

# Phase 01: Build, validate, and run isolated evaluator

## Context links

- Contract: `C:/Users/trand/.codex/attachments/fc2fddea-cf35-4eb7-afd9-bed365b1d459/pasted-text.txt:5`
- Reference evaluator: `C:/Users/trand/Downloads/Others/deimv2_phase5_tiling_eval.py:29`
- Successful training kernel: `artifacts/kaggle-latest-kernel/deimv2-visdrone-train.py:2379`
- Current training metadata: `artifacts/kaggle-latest-kernel/kernel-metadata.json:2`

## Overview

Create an inference-only Kaggle kernel beside, never over, the successful training kernel. Treat input identity, taxonomy, checkpoint compatibility, and baseline reproduction as fail-closed gates before interpreting tiling.

## Requirements and architecture

- Checkpoint persistence: save Phase-4 `best.pth` (preferred) or `best_stg1.pth` as a versioned private Kaggle Dataset; record Dataset slug/version, filename, byte count, SHA-256, selected `ema.module`/`model`, and checkpoint epoch where available. Never depend on `/kaggle/working` across sessions (contract lines 45-49). Do not use the training kernel fallback that aliases `last.pth` to `best.pth` (`artifacts/kaggle-latest-kernel/deimv2-visdrone-train.py:2938`).
- Environment: one T4, internet enabled, current Kaggle torch stack retained; clone official DEIMv2 and detach exact commit `0fff8d4dcdc272e6cf2d84be31399db471357941` as already proven by the training kernel (`artifacts/kaggle-latest-kernel/deimv2-visdrone-train.py:288`, `artifacts/kaggle-latest-kernel/deimv2-visdrone-train.py:335`). Apply and verify only the known torchvision-v2 aliases (`artifacts/kaggle-latest-kernel/deimv2-visdrone-train.py:425`, `artifacts/kaggle-latest-kernel/deimv2-visdrone-train.py:515`).
- Inputs: attach the checkpoint Dataset and existing VisDrone Dataset currently named in metadata (`artifacts/kaggle-latest-kernel/kernel-metadata.json:15`). Require exactly one annotation file, 548 unique image IDs, every referenced image, unique filenames after resolution, valid dimensions/bboxes, and log actual retained/dropped annotation counts.
- Taxonomy: because this source contract declares annotation IDs as raw VisDrone semantics, force `1..10 -> 0..9`, drop `0,11`, and write a new normalized JSON plus taxonomy audit; never infer “already zero-based” merely because a particular split lacks IDs 10/11. The reference’s heuristic branches on observed IDs (`C:/Users/trand/Downloads/Others/deimv2_phase5_tiling_eval.py:314`) and is a correctness gap. Verify category names/order and assert every output annotation ID is `0..9`.
- Model: config is DEIMv2-S, DINOv3 distilled ViT-Tiny, 640 input, 10 classes, `remap_mscoco_category=False` (`C:/Users/trand/Downloads/Others/deimv2_phase5_tiling_eval.py:466`). Resolve exactly one real `vitt_distill.pt`, preferably attached; verify expected size range and SHA-256. Load `ema.module`, else `model`, with `strict=True`, then deploy model and postprocessor (`C:/Users/trand/Downloads/Others/deimv2_phase5_tiling_eval.py:493`). Any mismatch stops.
- Common inference: PIL RGB -> resize 640x640 -> tensor -> ImageNet normalization (`C:/Users/trand/Downloads/Others/deimv2_phase5_tiling_eval.py:533`); score floor `0.001`; same model instance/checkpoint and ordered image list across modes.
- Baseline: full original image, original width/height into postprocessor, no external NMS (`C:/Users/trand/Downloads/Others/deimv2_phase5_tiling_eval.py:727`). Run and evaluate baseline first; stop before tiled modes when `abs(AP50:95 - 0.2271) > 0.015` (the reference currently warns only after all runs at line 1004).
- Tiles: native crops up to 640; overlap 0 or 0.25; deterministic final edge shift with no duplicates; postprocessor receives crop size; restore offsets, clip, remove degenerate boxes, class-aware NMS IoU `0.60`, global score order, maximum 300/original image. Evaluate only against original-image GT. Reference seams: positions/tiles (`C:/Users/trand/Downloads/Others/deimv2_phase5_tiling_eval.py:587`), merge (`C:/Users/trand/Downloads/Others/deimv2_phase5_tiling_eval.py:634`).
- Timing: warm up each distinct shape/mode, synchronize CUDA immediately around forward measurement, and report forward sum plus end-to-end wall time per original image; tiled end-to-end includes crop/transform/transfers/offset/clip/NMS. Reset peak allocated VRAM per experiment. Record mean, median, p95 latency (mean is contractual), FPS=`N/total timed seconds`, tiles/image, prediction count. Exclude setup, file serialization, and COCOeval.
- Metrics: COCOeval AP50:95, AP50, AP75, AP-small/medium/large, AR@100, AR-small/medium/large; use all original image IDs (`C:/Users/trand/Downloads/Others/deimv2_phase5_tiling_eval.py:861`).
- Outputs under `/kaggle/working/phase5_deimv2_tiling/`: three required prediction JSONs, normalized annotation copy, taxonomy/provenance audit, and `phase5_summary.{json,csv,md}`. Put all metrics, timing, provenance, and deltas (`delta_AP50_95`, `delta_AP_small`, `delta_AR_small`, `latency_multiplier`) in JSON and CSV as well as Markdown; reference currently emits deltas only in Markdown (`C:/Users/trand/Downloads/Others/deimv2_phase5_tiling_eval.py:919`). Save partial summary atomically after each completed experiment.

## Implementation steps

1. Create/version the private checkpoint Dataset from the successful Phase-4 output; download or API-inspect it once and capture immutable identity/hash. Attach it to the new kernel metadata; never add it to the training kernel.
2. Copy the reference evaluator into the new owned artifact, then apply the gates and output corrections above. Create separate metadata using a new kernel ID, one T4, internet enabled, VisDrone + checkpoint Dataset sources; preserve the existing pinned container digest unless Kaggle rejects it (`artifacts/kaggle-latest-kernel/kernel-metadata.json:22`).
3. Extract pure helpers for unit-testability only if needed; keep one script and no new service/classes. Add local tests or an embedded preflight for raw mapping, ambiguous taxonomy rejection, edge-tile uniqueness, coordinate restoration/clipping, per-class NMS, 300 cap, delta calculation, and output schema.
4. Run `python -m py_compile` and CPU-safe helper tests locally. Verify metadata JSON and grep that the new script contains no train/optimizer/backward/torchrun path.
5. Push with `kaggle kernels push -p artifacts/kaggle-phase5-deimv2-tiling`; poll `kaggle kernels status <new-slug>` to terminal state. On failure, download logs, fix only the new kernel, repush a new version.
6. First execute baseline gate (configuration flag or deliberate early-stop run). After it passes, run all modes. Download output with `kaggle kernels output <new-slug> -p <run-artifact-dir>` and audit every artifact before conclusions.
7. Compare modes in contractual order: AP-small, AR-small, latency/FPS, AP50:95. Mark tiling useful only with stated quantitative gain and acceptable observed cost; targets are not pass guarantees.

## Test matrix

| Level | Cases | Pass condition |
|---|---|---|
| Unit | raw IDs 0/1/10/11; suspicious 0..9-only raw input; tile sizes `<640`, `=640`, non-multiple, overlap; duplicate edges; offset/clip; class-aware overlap; 300 cap; deltas | Exact mappings/tiles/boxes/order; ambiguous source fails closed |
| Integration | synthetic COCO fixture + fake deterministic model/postprocessor; empty detections; duplicate filenames/checkpoints; strict state mismatch; output interruption | Original IDs/categories preserved; required partial outputs valid; every invalid input stops clearly |
| Kaggle smoke | pinned commit, Dataset identity/hash, backbone, strict load, 3 warmups, one val image per mode | Same provenance/config; finite boxes/scores/timings; T4 only |
| Kaggle E2E | 548 images, baseline then both tile modes, COCOeval, artifact download | Baseline tolerance passes; 3 prediction files cover same image universe; summaries contain all metrics/deltas/provenance |

## Risks, mitigation, rollback

| Risk (likelihood x impact) | Mitigation | Rollback |
|---|---|---|
| Wrong checkpoint or mutable Dataset (M x H) | Immutable Dataset version + SHA-256 + strict load + baseline gate | Stop run; attach correct Dataset version; no results interpreted |
| Taxonomy silently shifts classes (M x H) | Contract-forced raw mapping, category-name assertions, audit counts | Delete working normalized copy/output version; original Dataset untouched |
| Timing comparison biased (M x H) | One T4, per-mode warmup, synchronization, fixed order/protocol, distribution stats | Rerun all modes under one fresh kernel version; discard mixed-runtime results |
| Tile boundary duplicates inflate FP (M x H) | Unique edge coordinates + class-aware NMS + unit fixture | Revert new kernel version; adjust tile/merge helper only, rerun all tiled modes |
| Kaggle run/quota/network failure (M x M) | Prefer attached weights, atomic partial summaries, status/log workflow | Retry new kernel version; Phase-4 training kernel and Dataset remain unchanged |
| Baseline mismatch (M x H) | Hard gate before tiled runs, inspect hash/config/preprocess/taxonomy | Stop interpretation and restore last verified evaluator version |

Rollback is isolated: disable/archive the new Phase-5 kernel version and remove its generated outputs. Never mutate/delete the Phase-4 kernel, checkpoint Dataset version, or source VisDrone Dataset.

## Todo

- [x] Checkpoint Dataset slug/version/hash captured and attached
- [x] Separate kernel files created with exclusive ownership
- [x] Input/taxonomy/model gates implemented
- [x] Baseline and tiling data flows implemented
- [x] Unit/integration/static checks pass
- [x] Baseline reproduction gate passes on one T4
- [x] Full Kaggle run succeeds and outputs downloaded/audited
- [x] Quantitative decision recorded without scope expansion

## Delivery evidence

- Kaggle kernel `shirin21st/deimv2-phase-5-tiling-evaluation`: terminal status `COMPLETE`; one Tesla T4.
- Checkpoint Dataset: `shirin21st/deimv2-s-visdrone-phase4-best`; local `best.pth` 156,501,182 bytes; SHA-256 `DBE9665CD9DACB530629229545C9BED6FF50C2B7E5244EC90065915D184294CC`.
- Downloaded outputs: three prediction JSON files plus `phase5_summary.{json,csv,md}` under `artifacts/phase5-results/phase5_deimv2_tiling/`.
- Baseline AP50:95 `0.2271268`; reference delta `0.0000268`, inside `0.015` gate.
- Best mode `tile640_overlap25`: AP-small `0.1849`, AR-small `0.3608`, AP50:95 `0.2744`; latency `180.4 ms/image`, `4.09x` baseline.
- Decision report: `reports/deimv2_phase5_tiling_report.md`.
- Verification evidence: `plans/reports/tester-260807-phase5-results.md` records source compilation/integrity and validates every downloaded prediction entry plus summary consistency.

## Unresolved questions

- Whether the approximately fourfold latency increase is acceptable on target deployment hardware.
