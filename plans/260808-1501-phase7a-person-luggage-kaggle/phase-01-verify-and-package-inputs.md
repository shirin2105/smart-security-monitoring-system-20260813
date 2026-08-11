---
phase: 1
title: "Verify and package inputs"
status: completed
priority: P1
effort: "45m"
dependencies: []
---

# Phase 1: Verify and Package Inputs

## Context Links

- Source contract: [guide](C:/Users/trand/Downloads/Others/PHASE7A_AGENT_GUIDE.md:20)
- Script discovery guards: [script](C:/Users/trand/Downloads/Others/phase7a_person_luggage_deimv2_kaggle.py:206)
- Existing Kaggle convention: [phase5b metadata](../../kaggle_pipeline/phase5b_kernel/kernel-metadata.json:1)

## Overview

Create a new private Phase 7A Kaggle script package. Attach only verified immutable inputs; record slugs, versions, sizes, and hashes before push.

## Requirements and Architecture

- Attach `duwipurnamasidik/visdrone-2019-coco-format`; prove one each train/val VisDrone JSON plus resolvable train/val images.
- Attach `shirin21st/deimv2-s-visdrone-phase4-best`; prove exactly one Phase-4 `best.pth`, preferably named `deimv2_phase4_best.pth`. Never use ECDet.
- Attach verified `awsaf49/coco-2017-dataset`; re-prove `instances_train2017.json`, `instances_val2017.json`, `train2017` images, `val2017` images, and category IDs/names 1/person, 27/backpack, 31/handbag, 33/suitcase at execution time.
- Package the supplied Python script; preserve its locked mappings ([script](C:/Users/trand/Downloads/Others/phase7a_person_luggage_deimv2_kaggle.py:64)) and pinned DEIM commit ([script](C:/Users/trand/Downloads/Others/phase7a_person_luggage_deimv2_kaggle.py:61)). Enable private, Internet ON unless ViT-T is attached, GPU, and T4x2 where Kaggle supports it.

## Related Files and Ownership

- Create/own: `kaggle_pipeline/phase7a_kernel/phase7a_person_luggage_deimv2_kaggle.py`, `kaggle_pipeline/phase7a_kernel/kernel-metadata.json`.
- Read only: prior Kaggle metadata and Phase-4 checkpoint dataset.

## Implementation Steps

1. Copy supplied script byte-for-byte; record SHA-256 for source and packaged copy.
2. Inspect Kaggle dataset file lists before attaching; reject missing, duplicate, miniature, annotation-only, or image-only COCO candidates.
3. Create metadata with exactly the three required dataset sources (plus optional ViT-T source), private visibility, Internet/GPU settings, and a unique kernel slug.
4. Run Python syntax compile, JSON parse, source hash equality, metadata lint, and locked-constant grep.

## Test Matrix and Success Criteria

| Level | Check | Pass condition |
|---|---|---|
| Static | script + metadata | compile/parse; hashes and locked constants match |
| Integration | input inventory | four annotation JSONs, both image splits, exactly one checkpoint resolvable |
| Contract | policy | COCO category IDs/names valid; no whole-COCO-person selection change |

- [x] Dataset slugs/versions and inventories recorded.
- [x] Package has no taxonomy/data/model/training changes.
- [x] T4x2 requested; single-T4 fallback acknowledged, not silently treated as equivalent runtime.

## Risk Assessment and Rollback

- High likelihood × high impact: mislabeled/incomplete COCO mirror. Mitigate with file inventory, JSON category check, image sampling, and nonzero train/val counts before push.
- Medium × high: wrong checkpoint. Mitigate explicit Phase-4 provenance/hash and filename; script resolver also rejects ambiguity ([script](C:/Users/trand/Downloads/Others/phase7a_person_luggage_deimv2_kaggle.py:217)).
- Rollback: delete/recreate only the new Phase 7A package; never mutate input datasets or prior kernels.

## Next Steps

Proceed only when all preflight evidence passes. Block Phase 2 otherwise.

## Unresolved Questions

None.
