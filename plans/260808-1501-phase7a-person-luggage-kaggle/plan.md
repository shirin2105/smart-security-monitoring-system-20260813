---
title: "Phase 7A person-luggage DEIMv2 Kaggle execution"
description: "Package, gate, run, retrieve, and audit the locked Phase 7A DEIMv2-S training and evaluation workflow on Kaggle."
status: completed
priority: P1
effort: 2h operator time plus Kaggle runtime
branch: model-CV-v1
tags: [deimv2, kaggle, visdrone, coco, training, evaluation]
created: 2026-08-08
---

# Phase 7A Person-Luggage DEIMv2 Kaggle Execution

## Outcome

Run the supplied script unchanged in intent: build the four-class VisDrone+COCO manifests, pass the one-epoch smoke gate, fine-tune DEIMv2-S for 20 epochs from the Phase-4 checkpoint, evaluate one `best.pth` across six dataset/mode jobs, and download the exact checkpoint, audit, summary, logs, and prediction evidence.

## Locked Scope

- Taxonomy, data selection, architecture, hyperparameters, and evaluation remain exactly as specified in the guide ([guide](C:/Users/trand/Downloads/Others/PHASE7A_AGENT_GUIDE.md:3), [forbidden changes](C:/Users/trand/Downloads/Others/PHASE7A_AGENT_GUIDE.md:222)).
- Permitted edits after failure: compatibility, Kaggle path, config serialization, dependency, or runtime fixes only; preserve `-t` tuning semantics ([guide](C:/Users/trand/Downloads/Others/PHASE7A_AGENT_GUIDE.md:120), [script](C:/Users/trand/Downloads/Others/phase7a_person_luggage_deimv2_kaggle.py:915)).
- No Phase 7B/ByteTrack work until results are reviewed.

## Phases

| Phase | Status | Deliverable | Depends on |
|---|---|---|---|
| [1](phase-01-verify-and-package-inputs.md) | completed | Provenance-verified private Kaggle package | — |
| [2](phase-02-submit-and-pass-smoke-gate.md) | completed | Submitted T4x2 run with `[SMOKE PASS]` | 1 |
| [3](phase-03-train-evaluate-and-monitor.md) | completed | Terminal successful train + six evaluations | 2 |
| [4](phase-04-download-audit-and-handoff.md) | completed | Verified local artifacts and Phase 7A report | 3 |

## Data Flow

`Kaggle inputs (VisDrone + verified COCO + Phase-4 best + optional ViT-T)` → supplied script → absolute-path four-class manifests + audit → smoke config/train → full 20-epoch tune via `-t` → `best.pth` → 3 validation subsets × 2 inference modes → summary/predictions/logs → local artifact bundle and decision report.

## Dependency and Ownership

Strict chain: input verification → smoke pass → full train/eval → retrieval. One operator owns the Phase 7A kernel/package files; later phases consume them without concurrent edits. Existing Phase 5/6 packages are read-only references.

## Global Success Criteria

- Required console markers and source/class counts captured.
- Exact required paths downloaded: `outputs/phase7a_deimv2_s_person_luggage/best.pth`, `phase7a_eval/phase7a_eval_summary.json`, `phase7a_person_luggage_dataset/dataset_audit.json`.
- Summary contains six dataset/mode results, overall metrics, per-class metrics, FPS, tiles/image, and VRAM.
- No unapproved model/data/taxonomy/training drift; warnings and compatibility fixes recorded.

## Rollback

Keep prior Kaggle versions and immutable input datasets. On failure, stop before the next gate, preserve logs/output, revert only the Phase 7A package to the last known hash, and resubmit a new version. Existing Phase-4/5/6 artifacts remain untouched.

## Unresolved Questions

None. Verified COCO source: `awsaf49/coco-2017-dataset`.
