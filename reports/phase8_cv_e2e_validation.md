# Phase 8 CV E2E validation status

Phase 8 dataset preparation is complete and the frozen Kaggle benchmark is
running. No metric is reported before complete 20/20 prediction coverage and
manual FP/FN attribution.

## CAVIAR validation set

- Kaggle Dataset: `shirin21st/phase8-caviar-cv-validation`, private, version 2.
- 20 original MPEG surveillance videos; no transcoding.
- 20 source XML annotations and 20 per-camera rule configurations.
- 886.72 seconds total, 25 FPS, 384×288.
- Selection: 5 abandoned/object, 5 crowd/group, 5 intrusion/Walk, and 5
  negative/mixed clips.
- Ground truth: 5 abandoned candidates, 5 crowd episodes, and 35 person-level
  zone intrusions.

The project event schema is derived before inference from CAVIAR XML and fixed
camera ROIs. `LeftBag_BehindChair` is the sole disclosed manual annotation because
its occluded bag is not represented as an XML object. The other four abandoned
events use CAVIAR's `leaving object` role directly.

## Frozen benchmark

- DEIMv2-S Phase 7A checkpoint; no retraining.
- Generic class-wise ByteTrack runtime; no tracker replacement.
- Current Phase 7C quality, stitching, stationary, owner, and owner-away logic.
- `full640` on the 384×288 CAVIAR clips.
- Unified JSONL for `ZONE_INTRUSION`, `CROWD_THRESHOLD`, and candidate-level
  `ABANDONED_OBJECT`.

Kaggle kernel version 1 failed before inference because Kaggle only materialized
the entrypoint and `phase8_batch_runner.py` was absent. The fix publishes the
support tree as private Dataset `shirin21st/deimv2-phase8-code-bundle`; the
entrypoint accepts Kaggle's expanded Dataset layout or a local ZIP layout.
Kernel version 2 then exposed a UTF-8 BOM in the staged Kaggle manifest. JSON
loading now uses `utf-8-sig`, which accepts both BOM and BOM-free UTF-8 without
changing validation semantics. Code Dataset version 2 and kernel version 3 were
published on 2026-08-10; the first v3 status check returned `RUNNING`.
Kernel v3 completed detector/tracker processing for `LeftBag` but then proved the
runtime bundle omitted `kaggle_pipeline/phase7c_kernel/phase7c_core.py`. The
bundle builder now includes and validates the full Phase 7C core path. Code
Dataset v3 and kernel v4 were published; the first v4 status check returned
`RUNNING`.

## Verification

- Dataset manifest validator: pass, 20 clips with positive/negative coverage for
  all three event types.
- Kaggle Dataset listing: pass, 65 files including all 20 videos.
- Phase 8 focused tests: 26/26 pass, including zipped/expanded code layouts,
  the exact UTF-8 BOM regression, and an isolated bundle import/execution of
  Phase 7C abandoned reasoning.
- Python compilation: pass for the CAVIAR parser/preparer.
- Batch remains fail-closed: evaluation requires 20/20 successful clips and
  measured processed duration.

## Remaining gates

1. Kaggle batch finishes and outputs are downloaded.
2. `evaluate_events.py` computes event P/R/F1, false-rate, and delay.
3. A human reviews every unmatched event and replaces `UNKNOWN` attribution.

Until those gates close, Phase 8 remains **in progress** and there is no accuracy,
false-alarm, or completion claim. Abandoned results remain candidate-only.

## Unresolved questions

- Which component dominates errors after the reviewed 20-video benchmark?
