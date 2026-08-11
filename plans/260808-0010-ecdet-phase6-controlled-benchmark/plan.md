# Phase 6 ECDet controlled benchmark

## Goal

Train ECDet-S on the unchanged VisDrone train/val split, then compare the same
best checkpoint with frozen DEIMv2 Phase-5B references.

## Phases

- [x] Review guide, source scripts, existing Kaggle conventions.
- [ ] Package both exact source scripts and a sequential launcher.
- [ ] Validate hashes, syntax, metadata, and contract constants.
- [ ] Push one Kaggle kernel with VisDrone input, Internet ON, GPU enabled.
- [ ] Monitor smoke, 20-epoch training, and evaluation to terminal status.
- [ ] Download outputs and verify checkpoint, metrics, comparison, warnings.
- [ ] Update project reports/docs after verified completion.

## Locked constraints

- EdgeCrafter commit `706d037c17c1703bb97f42a35d269959b511b5be`.
- ECDet-S only; 20 epochs; input 640; AMP/EMA; seed 0.
- Raw VisDrone 0/11 dropped and 1..10 mapped to model IDs 0..9.
- Smoke must pass before full training.
- No DEIM retraining, S4/P2, YOLO, VLM, data/taxonomy changes, or Phase 7.
- Training uses two GPUs when available; evaluation uses `cuda:0`.

## Deliverables

- `kaggle_pipeline/phase6_kernel/`
- `/kaggle/working/outputs/phase6_ecdet_s_visdrone_full20/best.pth`
- `/kaggle/working/phase6_ecdet_vs_deim/phase6_comparison.{json,csv,md}`
- Exact smoke line, best epoch/metrics/checkpoint, final table, deltas, warnings.

## Failure policy

Return the complete traceback and explain root cause before any compatibility
change. Never bypass smoke or change taxonomy, metrics, or architecture.

## Unresolved questions

- Kaggle may expose one T4 despite requesting GPU; script safely uses one GPU
  with batch 8 in that case, while preserving all other controlled settings.
