# DEIMv2 Phase 5 — Tiled inference report

## Scope

Phase 5 evaluated one trained DEIMv2-S VisDrone checkpoint without retraining. All experiments used the same 548-image validation set, model input 640×640, score floor 0.001, and one Tesla T4. YOLO and VLM are not part of the project flow.

Implemented experiments:

- `baseline_640`: resize the complete image to 640×640; official DEIMv2 postprocessing; no external NMS.
- `tile640_no_overlap`: native 640×640 crops, no overlap, coordinate restoration, class-aware NMS at IoU 0.60.
- `tile640_overlap25`: native 640×640 crops with 25% overlap and the same merge policy.

The submitted evaluator code specifies the pinned DEIMv2 commit `0fff8d4dcdc272e6cf2d84be31399db471357941`, strict checkpoint loading, normalized VisDrone category IDs, CUDA synchronization for timing, COCO evaluation, and a maximum of 300 merged detections per image.

## Results

| Experiment | AP50:95 | AP50 | AP-small | AR-small | Latency ms/image | FPS | Tiles/image |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline_640 | 0.2271 | 0.3876 | 0.1313 | 0.2747 | 44.1 | 22.68 | 1.00 |
| tile640_no_overlap | 0.2647 | 0.4556 | 0.1783 | 0.3520 | 181.7 | 5.50 | 5.12 |
| tile640_overlap25 | 0.2744 | 0.4628 | 0.1849 | 0.3608 | 180.4 | 5.54 | 5.19 |

Baseline AP50:95 differed from the Phase-4 reference `0.2271` by only `0.00003`, well inside the `0.015` sanity tolerance.

Compared with baseline, `tile640_overlap25` produced:

- `+0.0472` AP50:95;
- `+0.0536` AP-small;
- `+0.0861` AR-small;
- approximately `4.09×` end-to-end latency.

## Decision

Native-resolution tiled inference materially improved distant/small-object performance. The 25% overlap mode reached the strong Phase-5 targets (`AP-small ≥ 0.18`, `AR-small ≥ 0.35`) and was the best accuracy configuration. It is a valid deployment candidate when small-object recall has priority, but its roughly fourfold latency cost requires a separate throughput/deployment decision.

## Artifacts

- Machine-readable summaries: `reports/phase5/phase5_summary.json` and `.csv`.
- Original Kaggle Markdown summary: `reports/phase5/phase5_summary.md`.
- Full downloaded predictions remain under `artifacts/phase5-results/phase5_deimv2_tiling/` and are intentionally excluded from Git because they total about 72 MB.
- Kaggle kernel: `shirin21st/deimv2-phase-5-tiling-evaluation`.

## Evidence limitations

The retained Kaggle summaries contain metrics and runtime measurements only. They do not embed the checkpoint hash, DEIMv2 commit, taxonomy audit, baseline tolerance calculation, or delta fields in JSON/CSV. Those implementation settings are verifiable in the byte-identical submitted evaluator source, while the numerical deltas above were recalculated from the downloaded JSON. The normalized working annotation was written outside the result directory and was not retained in the downloaded Phase-5 bundle.

## Unresolved questions

- Whether the approximately fourfold latency increase is acceptable on target deployment hardware.
