# DEIMv2 Phase 5 — Tiling / ROI inference comparison

| Experiment | AP50:95 | AP50 | AP-small | AR-small | Latency ms/img | FPS | Avg tiles/img | Peak VRAM MB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline_640 | 0.2271 | 0.3876 | 0.1313 | 0.2747 | 44.1 | 22.68 | 1.00 | 92.3 |
| tile640_no_overlap | 0.2647 | 0.4556 | 0.1783 | 0.3520 | 181.7 | 5.50 | 5.12 | 92.3 |
| tile640_overlap25 | 0.2744 | 0.4628 | 0.1849 | 0.3608 | 180.4 | 5.54 | 5.19 | 92.3 |

## Delta vs baseline

| Experiment | ΔAP50:95 | ΔAP-small | ΔAR-small | Latency multiplier |
|---|---:|---:|---:|---:|
| baseline_640 | +0.0000 | +0.0000 | +0.0000 | 1.00x |
| tile640_no_overlap | +0.0376 | +0.0470 | +0.0773 | 4.12x |
| tile640_overlap25 | +0.0472 | +0.0536 | +0.0861 | 4.09x |
